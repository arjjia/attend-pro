from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://attendpro:attendpro@localhost:5432/attendpro"
    jwt_secret: str = "development-only-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    seed_date: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
