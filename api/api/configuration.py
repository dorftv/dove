from fastapi import FastAPI, APIRouter

from config_handler import ConfigReader  # make sure to replace with your actual module name

router = APIRouter()

config_reader = ConfigReader('/app/config.toml')

@router.get("/config")
def get_config():
    return config_reader.get_config()
