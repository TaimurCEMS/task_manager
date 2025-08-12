# File: /app/core/config.py | Version: 1.2 | Title: Central App Settings (Pydantic v2)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Database ---
    DATABASE_URL: str = "sqlite:///./app.db"

    # --- Security / JWT ---
    SECRET_KEY: str = "CHANGE_ME_FOR_DEV_ONLY"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # --- API behavior toggles ---
    ENABLE_STD_ERRORS: bool = (
        False  # set True in .env to enable standardized error responses
    )

    # v2-style config
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
