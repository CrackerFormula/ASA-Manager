from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    MAP_NAME: str = "TheIsland_WP"
    SESSION_NAME: str = "ARK Server"
    SERVER_ADMIN_PASSWORD: str = "changeme"
    SERVER_PASSWORD: str = ""
    MAX_PLAYERS: int = 70
    ASA_PORT: int = 7777
    RCON_PORT: int = 27020
    RCON_ENABLED: bool = True
    BATTLEYE: bool = False
    MOD_IDS: str = ""
    CUSTOM_SERVER_ARGS: str = ""
    INI_PATH: str = "/serverdata/config/GameUserSettings.ini"
    ARK_LOG_PATH: str = "/serverdata/ark-server/ShooterGame/Saved/Logs/ShooterGame.log"
    SERVER_DIR: str = "/serverdata/ark-server"
    WEB_PASSWORD: str = ""
    SESSION_MAX_AGE: int = 86400
    SECURE_COOKIES: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
