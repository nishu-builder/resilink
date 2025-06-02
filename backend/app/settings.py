from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List, Optional

from typing_extensions import Annotated

from pydantic import BeforeValidator


def parse_comma_separated_string(value: str) -> Optional[List[str]]:
    """Parse comma-separated string into list of strings."""
    if not value:
        return None
    return [item.strip() for item in value.split(",")]


class Settings(BaseSettings):
    # Database
    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None
    POSTGRES_DB: str | None = None

    # CORS
    ALLOWED_ORIGINS: Annotated[Optional[List[str]], BeforeValidator(parse_comma_separated_string)] = None

    # General
    app_name: str = "Hazard Analysis Platform"
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=[".env", ".env.example"], env_file_encoding="utf-8")

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return f'postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@postgres:5432/{self.POSTGRES_DB}'

    @property
    def database_url(self) -> str:
        return f'postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@postgres:5432/{self.POSTGRES_DB}'


@lru_cache
def get_settings() -> Settings:  # pragma: no cover
    return Settings() 
