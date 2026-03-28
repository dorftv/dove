"""OIDC authentication with cookie-based BFF pattern.

When auth.enabled=false (default), all checks are no-ops.
When enabled, uses Authorization Code flow with PKCE via authlib.
Tokens stored in signed httpOnly cookies — frontend is auth-transparent.
"""

import os
import time
import secrets
from dataclasses import dataclass
from typing import Optional

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.jose import jwt, JoseError
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature
from starlette.requests import HTTPConnection

from config_handler import ConfigReader
from logger import logger

config = ConfigReader()
router = APIRouter(prefix="/auth", tags=["Auth"])


@dataclass
class UserInfo:
    sub: str
    username: str
    email: str
    groups: list[str]
    access_token: str
    refresh_token: str
    expires_at: float


# --- Module state (initialized lazily) ---

_auth_config: dict = {}
_cookie_signer: Optional[URLSafeTimedSerializer] = None
_jwks: Optional[dict] = None
_oidc_metadata: Optional[dict] = None
_jwks_fetched_at: float = 0

COOKIE_NAME = "dove_session"
COOKIE_MAX_AGE = 86400  # 24h
PROACTIVE_REFRESH_SECS = 30  # refresh token if expires within this window


def _validate_redirect_base(request: Request, redirect_base: Optional[str]) -> str:
    """Validate redirect_base against allowed origins to prevent open redirect."""
    server_origin = str(request.base_url).rstrip('/')
    if not redirect_base:
        return server_origin
    cfg = _get_config()
    allowed = cfg.get('allowed_origins', [])
    # Always allow same-origin
    if redirect_base == server_origin:
        return redirect_base
    if redirect_base in allowed:
        return redirect_base
    logger.log(f"Rejected redirect_base: {redirect_base}", level='WARNING')
    return server_origin


def _get_config() -> dict:
    global _auth_config, _cookie_signer
    if not _auth_config:
        _auth_config = config.get_auth_config()
        secret = _auth_config.get('cookie_secret')
        if not secret:
            secret = secrets.token_hex(32)
        _cookie_signer = URLSafeTimedSerializer(secret)
    return _auth_config


def is_auth_enabled() -> bool:
    return _get_config().get('enabled', False)


async def _get_oidc_metadata() -> dict:
    """Fetch OIDC metadata. Uses internal_issuer for backend-to-IdP calls."""
    global _oidc_metadata
    if _oidc_metadata:
        return _oidc_metadata
    cfg = _get_config()
    internal = cfg['internal_issuer'].rstrip('/')
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{internal}/.well-known/openid-configuration")
            resp.raise_for_status()
            _oidc_metadata = resp.json()
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout, OSError) as e:
        logger.log(f"OIDC discovery failed: {e}", level='WARNING')
        raise HTTPException(status_code=503, detail="Auth service temporarily unavailable")
    public = cfg['issuer'].rstrip('/')
    if internal != public:
        # server-to-server calls need internal hostname (token exchange + JWKS fetch)
        _oidc_metadata['token_endpoint'] = _oidc_metadata['token_endpoint'].replace(public, internal)
        _oidc_metadata['jwks_uri'] = _oidc_metadata['jwks_uri'].replace(public, internal)
    return _oidc_metadata


async def _get_jwks() -> dict:
    global _jwks, _jwks_fetched_at
    if _jwks and (time.time() - _jwks_fetched_at < 3600):
        return _jwks
    meta = await _get_oidc_metadata()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(meta['jwks_uri'])
            resp.raise_for_status()
            _jwks = resp.json()
            _jwks_fetched_at = time.time()
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout, OSError) as e:
        logger.log(f"JWKS fetch failed: {e}", level='WARNING')
        raise HTTPException(status_code=503, detail="Auth service temporarily unavailable")
    return _jwks


def _create_cookie(response: Response, data: dict):
    signed = _cookie_signer.dumps(data)
    response.set_cookie(
        COOKIE_NAME,
        signed,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=_get_config().get('cookie_secure', True),
        path="/",
    )


def _read_cookie(request: HTTPConnection) -> Optional[dict]:
    raw = request.cookies.get(COOKIE_NAME)
    if not raw:
        return None
    try:
        return _cookie_signer.loads(raw, max_age=COOKIE_MAX_AGE)
    except BadSignature:
        return None


def _parse_groups(token_data: dict) -> list[str]:
    """Extract groups from JWT, stripping leading / from group paths."""
    groups = token_data.get('groups', [])
    return [g.lstrip('/') for g in groups] if isinstance(groups, list) else []


async def _refresh_tokens(refresh_token: str) -> Optional[dict]:
    """Use refresh token to get new access token."""
    try:
        cfg = _get_config()
        meta = await _get_oidc_metadata()
        async with httpx.AsyncClient() as client:
            resp = await client.post(meta['token_endpoint'], data={
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': cfg['client_id'],
                'client_secret': cfg['client_secret'],
            })
            if resp.status_code != 200:
                return None
            return resp.json()
    except Exception as e:
        logger.log(f"Token refresh failed: {e}", level='WARNING')
        return None


async def _decode_access_token(access_token: str) -> dict:
    """Decode and validate JWT access token."""
    jwks = await _get_jwks()  # may raise 503 on transient failure
    try:
        claims = jwt.decode(access_token, jwks)
        claims.validate()
        return dict(claims)
    except JoseError as e:
        logger.log(f"JWT decode failed: {e}", level='WARNING')
        raise HTTPException(status_code=401, detail="Invalid token")


# --- FastAPI dependencies ---

def _check_api_token(token: str) -> Optional[UserInfo]:
    """Check if token matches a configured static API token."""
    cfg = _get_config()
    for t in cfg.get('api_tokens', []):
        if secrets.compare_digest(t['token'], token):
            groups_map = cfg.get('groups', {})
            role = t.get('role', 'admin')
            group = groups_map.get(role, role)
            return UserInfo(
                sub=f"api-token:{t.get('name', 'unnamed')}",
                username=t.get('name', 'api'),
                email='',
                groups=[group],
                access_token=token,
                refresh_token='',
                expires_at=0,
            )
    return None


async def get_current_user(request: HTTPConnection, response: Response = None) -> Optional[UserInfo]:
    """Extract and validate user from session cookie or Bearer token.
    Returns None when auth is disabled (all access allowed).
    Auth order: cookie → static API token → OIDC JWT."""
    if not is_auth_enabled():
        return None

    # 1. Try session cookie (browser sessions)
    cookie = _read_cookie(request)
    if cookie and cookie.get('access_token'):
        expires_at = cookie.get('expires_at', 0)
        access_token = cookie.get('access_token', '')
        refresh_token = cookie.get('refresh_token', '')

        # Proactive refresh: if token expires soon, refresh now
        if time.time() > expires_at - PROACTIVE_REFRESH_SECS:
            new_tokens = await _refresh_tokens(refresh_token)
            if new_tokens:
                access_token = new_tokens['access_token']
                refresh_token = new_tokens.get('refresh_token', refresh_token)
                expires_at = time.time() + new_tokens.get('expires_in', 300)
                if response:
                    _create_cookie(response, {
                        'access_token': access_token,
                        'refresh_token': refresh_token,
                        'expires_at': expires_at,
                    })
            else:
                raise HTTPException(status_code=401, detail="Session expired")

        token_data = await _decode_access_token(access_token)

        return UserInfo(
            sub=token_data.get('sub', ''),
            username=token_data.get('preferred_username', ''),
            email=token_data.get('email', ''),
            groups=_parse_groups(token_data),
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
        )

    query_token = request.query_params.get('token')
    if query_token:
        api_user = _check_api_token(query_token)
        if api_user:
            return api_user

    auth_header = request.headers.get('authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]

        api_user = _check_api_token(token)
        if api_user:
            return api_user

        token_data = await _decode_access_token(token)
        return UserInfo(
            sub=token_data.get('sub', ''),
            username=token_data.get('preferred_username', ''),
            email=token_data.get('email', ''),
            groups=_parse_groups(token_data),
            access_token=token,
            refresh_token='',
            expires_at=token_data.get('exp', 0),
        )

    raise HTTPException(status_code=401, detail="Not authenticated")


async def get_current_user_optional(request: HTTPConnection) -> Optional[UserInfo]:
    """Like get_current_user but returns None for unauthenticated instead of 401."""
    if not is_auth_enabled():
        return None
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


def require_read():
    """Any authenticated role can read. No-op when auth disabled."""
    async def check(
        request: HTTPConnection,
        user: Optional[UserInfo] = Depends(get_current_user),
    ):
        pass  # get_current_user already raised 401 if not authenticated
    return Depends(check)


def require_role(*roles):
    """FastAPI dependency: check user has at least one of the required roles.
    Roles are DOVE role names (user/supervisor/outputs/admin), mapped to
    OIDC group names via config."""
    async def check(
        request: HTTPConnection,
        response: Response = None,
        user: Optional[UserInfo] = Depends(get_current_user),
    ):
        if user is None:  # Auth disabled
            return
        cfg = _get_config()
        groups_map = cfg.get('groups', {})
        admin_group = groups_map.get('admin', 'dove-admin')
        if admin_group in user.groups:
            return  # Admin bypasses all checks
        required_groups = [groups_map.get(r, r) for r in roles]
        if not any(g in user.groups for g in required_groups):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
    return Depends(check)


# --- Auth endpoints ---

@router.get("/login")
async def login(request: Request):
    """Redirect to OIDC provider login page."""
    if not is_auth_enabled():
        return RedirectResponse("/")
    cfg = _get_config()
    meta = await _get_oidc_metadata()
    redirect_base = _validate_redirect_base(
        request, request.query_params.get('redirect_base'))
    callback_url = f"{redirect_base}/auth/callback"
    client = AsyncOAuth2Client(
        client_id=cfg['client_id'],
        client_secret=cfg['client_secret'],
        redirect_uri=callback_url,
        scope='openid dove-groups',
    )
    uri, state = client.create_authorization_url(meta['authorization_endpoint'])
    response = RedirectResponse(uri)
    response.set_cookie("oauth_state", state, httponly=True, samesite="lax", max_age=600)
    response.set_cookie("oauth_redirect_base", redirect_base, httponly=True, samesite="lax", max_age=600)
    return response


@router.get("/callback")
async def auth_callback(request: Request):
    """Handle OIDC callback — exchange code for tokens, set session cookie."""
    if not is_auth_enabled():
        return RedirectResponse("/")
    cfg = _get_config()
    meta = await _get_oidc_metadata()
    # Must match the redirect_uri used in /login exactly
    redirect_base = request.cookies.get(
        'oauth_redirect_base', str(request.base_url).rstrip('/'))
    callback_url = f"{redirect_base}/auth/callback"
    client = AsyncOAuth2Client(
        client_id=cfg['client_id'],
        client_secret=cfg['client_secret'],
        redirect_uri=callback_url,
    )
    token = await client.fetch_token(
        meta['token_endpoint'],
        authorization_response=str(request.url),
    )
    response = RedirectResponse("/")
    _create_cookie(response, {
        'access_token': token['access_token'],
        'refresh_token': token.get('refresh_token', ''),
        'expires_at': time.time() + token.get('expires_in', 300),
    })
    return response


@router.get("/logout")
async def logout(request: Request):
    """Clear session cookie and redirect to OIDC provider logout."""
    redirect_base = _validate_redirect_base(
        request, request.query_params.get('redirect_base'))
    response = RedirectResponse("/")
    response.delete_cookie(COOKIE_NAME, path="/")
    if is_auth_enabled():
        try:
            meta = await _get_oidc_metadata()
            logout_url = meta.get('end_session_endpoint')
            if logout_url:
                response = RedirectResponse(
                    f"{logout_url}?post_logout_redirect_uri={redirect_base}"
                    f"&client_id={_get_config()['client_id']}"
                )
                response.delete_cookie(COOKIE_NAME, path="/")
        except Exception as e:
            logger.log(f"OIDC end-session lookup failed during logout: {e}", level='WARNING')
    return response


@router.get("/verify")
async def verify(request: Request):
    """Returns 200 if authenticated, 401 if not. For nginx auth_request."""
    if not is_auth_enabled():
        return Response(status_code=200)
    cookie = _read_cookie(request)
    if not cookie or not cookie.get('access_token'):
        return Response(status_code=401)
    try:
        await _decode_access_token(cookie['access_token'])
    except HTTPException as e:
        return Response(status_code=e.status_code)
    return Response(status_code=200)


@router.get("/me")
async def me(request: Request, response: Response):
    """Return current user info. Used by frontend to check auth state.
    Does not require auth — returns unauthenticated status if no valid session."""
    if not is_auth_enabled():
        return {"authenticated": False, "auth_enabled": False}
    try:
        user = await get_current_user(request, response)
        cfg = _get_config()
        groups_map = cfg.get('groups', {})
        dove_roles = [r for r, g in groups_map.items() if g in user.groups]
        return {
            "authenticated": True,
            "auth_enabled": True,
            "username": user.username,
            "email": user.email,
            "groups": user.groups,
            "roles": dove_roles,
        }
    except HTTPException:
        return {"authenticated": False, "auth_enabled": True}
