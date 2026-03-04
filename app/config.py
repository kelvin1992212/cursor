from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "House 88 WhatsApp AI System"
    database_url: str = "sqlite:///./house88.db"

    # WhatsApp Cloud API verification settings.
    whatsapp_verify_token: str = "house88-verify-token"
    whatsapp_api_url: str | None = None
    whatsapp_access_token: str | None = None

    # WeChat integration placeholder.
    wechat_api_url: str | None = None
    wechat_access_token: str | None = None

    # AI operating defaults.
    default_ai_enabled: bool = True
    default_ai_schedule_start: str = "20:00"
    default_ai_schedule_end: str = "09:00"
    default_timezone: str = "Asia/Hong_Kong"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
