# File: /app/core/config.py | Version: 1.1 | Title: Central App Settings (Pydantic v2 compliant)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Database ---
    DATABASE_URL: str = "sqlite:///./app.db"

    # --- Security / JWT ---
    SECRET_KEY: str = "CHANGE_ME_FOR_DEV_ONLY"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # v2 style (replaces old `class Config:`)
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Reusable singleton
settings = Settings()
