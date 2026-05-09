# Authentication & Authorization

DOVE supports optional OIDC authentication via any OpenID Connect provider (Keycloak, Authentik, Authelia, Google, etc.). When enabled, users must log in to access the application. When disabled (default), everything works without authentication.

## Quick Start

1. Set up your OIDC provider with groups and users (see below)
2. Add to your `config.toml`:

```toml
[auth]
enabled = true
issuer = "https://auth.example.com/realms/dove"
client_id = "dove-app"
client_secret = "your-secret"
```

3. Restart DOVE

## Configuration

```toml
[auth]
enabled = false       # default: no auth
issuer = ""           # OIDC issuer URL
client_id = ""        # OIDC client ID
client_secret = ""    # OIDC client secret (confidential client)
# cookie_secret = ""  # auto-generated if not set (sessions lost on restart)
# cookie_secure = true  # set false for local HTTP dev
# allowed_origins = []  # trusted redirect origins for multi-port dev setups

# Internal issuer URL for Docker deployments where the backend
# reaches the IdP via a different hostname than the browser.
# Example: issuer = "https://auth.example.com/realms/dove" (browser)
#          internal_issuer = "http://idp:8080/realms/dove" (backend)
# internal_issuer = ""

[auth.groups]
user = "dove-user"
supervisor = "dove-supervisor"
outputs = "dove-outputs"
admin = "dove-admin"
```

All settings can be overridden via environment variables:

| Variable | Config key |
|----------|-----------|
| `AUTH_ENABLED=true` | `auth.enabled` |
| `AUTH_ISSUER` | `auth.issuer` |
| `AUTH_INTERNAL_ISSUER` | `auth.internal_issuer` |
| `AUTH_CLIENT_ID` | `auth.client_id` |
| `AUTH_CLIENT_SECRET` | `auth.client_secret` |
| `AUTH_COOKIE_SECRET` | `auth.cookie_secret` |
| `AUTH_COOKIE_SECURE=false` | `auth.cookie_secure` |
| `AUTH_ALLOWED_ORIGINS` | `auth.allowed_origins` |

## Roles & Permissions

Permissions are based on OIDC groups. A user can have multiple groups (additive). The group names are configurable via `[auth.groups]`.

| Role | Group (default) | Permissions |
|------|----------------|-------------|
| User | `dove-user` | Create/delete inputs, cut program, add/remove sources in scenes, control playback, browse files, NodeCG dashboard access |
| Supervisor | `dove-supervisor` | Create/delete scenes, add/remove slots, edit slot properties (position, size, alpha, volume) |
| Outputs | `dove-outputs` | Create/delete outputs and encoders |
| Admin | `dove-admin` | Everything including config, debug pages, system settings |

Admin implicitly has all permissions. Typical role combinations:

- **Camera operator:** `dove-user`
- **Show director:** `dove-user` + `dove-supervisor`
- **Technical operator:** `dove-user` + `dove-supervisor` + `dove-outputs`
- **Administrator:** `dove-admin`

## Entity Locks

Inputs, outputs, encoders, and scenes can be individually locked via `config.toml` to prevent accidental changes in production:

| Field | Protects |
|-------|----------|
| `locked` | Deletion and settings changes on the entity |
| `src_locked` | Source/slot modifications in scenes |

When an entity is locked, the UI hides edit/delete controls. **Admin** users bypass all locks.

When auth is disabled, add `?unlocked=true` to the URL to bypass locks (dev/testing convenience). This is a UI-only safety net — locks are not enforced on the backend.

## How It Works

DOVE uses the Backend-for-Frontend (BFF) pattern:

1. User opens the app — if not logged in, redirected to the OIDC provider
2. After login, the provider redirects back to DOVE
3. DOVE exchanges the auth code for tokens and sets a secure httpOnly cookie
4. All subsequent requests (API, WebSocket, previews) carry the cookie automatically
5. Token refresh is handled server-side — transparent to the user

The frontend has no access to tokens (httpOnly cookie). UI elements are hidden based on roles, and the backend enforces permissions on every request.

## OIDC Provider Setup

DOVE requires an OIDC provider with group-based claims. Below is a generic setup — adapt to your provider.

### Groups

Create the following groups (or map existing ones via `[auth.groups]`):

- `dove-user`
- `dove-supervisor`
- `dove-outputs`
- `dove-admin`

### Client

Create an OpenID Connect client:

- **Client ID:** `dove-app`
- **Client authentication:** On (confidential)
- **Standard flow:** Enabled
- **Valid redirect URIs:** `https://your-dove-host/*`
- **Web origins:** `https://your-dove-host`

### Group Claim

Ensure group membership is included in the access token as a `groups` claim (array of group names). In Keycloak this is a "Group Membership" mapper with token claim name `groups` and "Full group path" off.

### Users

Create users and assign them to groups. A user needs at least `dove-user` to access the application.

## Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/auth/login` | Redirects to OIDC provider login |
| `/auth/callback` | Handles OIDC callback |
| `/auth/logout` | Clears session, redirects to provider logout |
| `/auth/me` | Returns current user info and roles (always accessible) |
| `/auth/verify` | Returns 200/401 for nginx `auth_request` (see below) |

## Always Open

These paths work without authentication even when auth is enabled:

- `/` (static SPA files)
- `/auth/*` (login flow)
- `/api/docs/*` (help pages)
- `/api/healthz` (Docker healthcheck — anonymous callers get a stripped response: status, uptime, pipeline state, error count; full error detail requires authentication)

## Protecting External Services with nginx

DOVE's `/auth/verify` endpoint returns 200 (authenticated) or 401 (not authenticated). Use nginx's `auth_request` directive to protect other services behind DOVE's login.

**Note:** NodeCG is proxied through DOVE natively (see [NodeCG docs](/help/inputs-nodecg)) — no nginx config needed for NodeCG.

```nginx
server {
    listen 443 ssl;

    # DOVE app — handles all DOVE routes including /auth/*
    location / {
        proxy_pass http://dove:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Example: protect another service with DOVE auth
    location /my-service/ {
        auth_request /auth/verify;
        proxy_pass http://my-service:8080/;
    }
}
```

This works because DOVE and the service share the same domain, so the browser sends DOVE's session cookie with every request. Nginx validates the cookie via DOVE before proxying.

## API Tokens for Scripts

When auth is enabled, admin scripts (e.g. restarting outputs via curl) need API access without browser login. DOVE supports two approaches:

### Static API Tokens

Configure long-lived tokens in `config.toml` — no OIDC provider interaction needed:

```toml
[[auth.api_tokens]]
token = "your-secret-here"
name = "admin-scripts"
role = "admin"
```

`role` defaults to `user` if omitted — set `role = "admin"` only for trusted scripts that need full access.

Or via environment variable (single token, convenient for Docker):

```
AUTH_API_TOKEN=your-secret-here
AUTH_API_TOKEN_NAME=admin-scripts
AUTH_API_TOKEN_ROLE=admin
```

Usage:

```bash
curl -H "Authorization: Bearer your-secret-here" http://dove:5000/api/outputs
```

### OIDC JWT (Short-Lived)

Get a token via your provider's password grant or client credentials flow:

```bash
TOKEN=$(curl -s https://auth.example.com/realms/dove/protocol/openid-connect/token \
  -d grant_type=password -d client_id=dove-app \
  -d client_secret=your-secret -d username=admin \
  -d password=admin | jq -r .access_token)

curl -H "Authorization: Bearer $TOKEN" http://dove:5000/api/outputs
```

Both methods work for REST API and WebSocket connections. The auth check order is: session cookie → static API token → OIDC JWT.

Browsers authenticate the WebSocket via the session cookie automatically. Headless clients must send the token as a WebSocket handshake header — query-string tokens are not supported:

```bash
wscat -H "Authorization: Bearer your-secret-here" -c ws://dove:5000/ws
```
