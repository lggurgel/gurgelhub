from typing import Literal
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

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
