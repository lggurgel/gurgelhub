from typing import Literal, Any, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    ADMIN_USERNAME: str
    ADMIN_PASSWORD_HASH: str
    ENVIRONMENT: Literal["development", "production"] = "development"

    # Search configuration
    SEARCH_RESULTS_PER_PAGE: int = 10
    SEARCH_SNIPPET_LENGTH: int = 150
    SEARCH_CACHE_TTL_SECONDS: int = 300

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str]) -> str:
        if isinstance(v, str):
            if v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
