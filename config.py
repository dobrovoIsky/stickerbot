import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    BOT_TOKEN: str = "YOUR_BOT_TOKEN_HERE"
    ADMIN_IDS: list[int] = []
    DATABASE_PATH: str = str(BASE_DIR / "database" / "bot.db")
    TEMP_DIR: str = str(BASE_DIR / "temp")
    SUBSCRIPTION_CACHE_SECONDS: int = 60
    MAX_IMAGE_SIZE_MB: int = 20

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

config = Settings()

# Ensure directories exist
os.makedirs(os.path.dirname(config.DATABASE_PATH), exist_ok=True)
os.makedirs(config.TEMP_DIR, exist_ok=True)
