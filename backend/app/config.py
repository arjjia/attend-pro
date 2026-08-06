from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://attendpro:attendpro@localhost:5432/attendpro"
    session_secret: str = "development-session-secret-change-me"
    session_expire_minutes: int = 1440
    session_cookie_secure: bool = False
    portal_private_key_path: str = "./data/portal-private-key.pem"
    portal_key_id: str = "attendpro-portal-p256-v1"
    device_credential_days: int = 30
    qr_ttl_seconds: int = 90
    clock_skew_seconds: int = 120
    enable_test_api: bool = True
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:9080,http://127.0.0.1:9080"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
