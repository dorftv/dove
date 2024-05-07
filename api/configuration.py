from fastapi import FastAPI, APIRouter

from config_handler import ConfigReader  # make sure to replace with your actual module name
config = ConfigReader()

router = APIRouter()

router = APIRouter(prefix="/api")


@router.get("/config")
def get_config():
    return config.get_config()

@router.get("/config/preview_enabled")
def get_config2():
    return config.get_preview_enabled()

@router.get("/config/mixers")
def get_config():
    return config.get_mixers()

@router.get("/config/resolutions")
def get_config():
    return config.get_resolutions()

@router.get("/config/default_resolution")
def get_config():
    return config.get_default_resolution()

@router.get("/config/proxy_types")
def get_config():
    return config.get_proxy_types()

