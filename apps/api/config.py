from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEVELOPMENT_ENCRYPTION_KEY = "7EQLH4k00_r0vSUQ5rAcw9tSF6cgBLf0WpwcXEzco50="


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="FLOWLEDGER_", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+psycopg://flowledger:flowledger@localhost:5432/flowledger"
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"
    secrets_encryption_key: str = _DEVELOPMENT_ENCRYPTION_KEY
    jwt_secret: str = "replace-this-development-jwt-secret-before-production"

    @model_validator(mode="after")
    def require_non_default_production_key(self) -> "Settings":
        if (
            self.environment.lower() not in {"development", "test"}
            and self.secrets_encryption_key == _DEVELOPMENT_ENCRYPTION_KEY
        ):
            raise ValueError("FLOWLEDGER_SECRETS_ENCRYPTION_KEY must be set outside development")
        if (
            self.environment.lower() not in {"development", "test"}
            and self.jwt_secret == "replace-this-development-jwt-secret-before-production"
        ):
            raise ValueError("FLOWLEDGER_JWT_SECRET must be set outside development")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
