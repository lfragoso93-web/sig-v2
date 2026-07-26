from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator
from typing import Optional


_DEFAULT_ADMIN_PASSWORD = "Admin@" + "1234!"
_DEFAULT_SECRET_KEY = "change-me-" + "in-production"


class Settings(BaseSettings):
    # O mesmo .env e compartilhado entre aplicacao, Docker Compose e rotinas
    # operacionais. Variaveis que pertencem a outros componentes nao devem
    # impedir a inicializacao desta classe nem a coleta da suite de testes.
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql://sgi:sgi@db:5432/sgi"
    ASYNC_DATABASE_URL: str = "postgresql+asyncpg://sgi:sgi@db:5432/sgi"
    APP_DEBUG: bool = False
    ENVIRONMENT: str = "development"

    SECRET_KEY: str = _DEFAULT_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    QUOTES_PROVIDER_TOKEN: Optional[str] = None
    MARKET_DATA_BASE_URL: Optional[str] = None
    MARKET_DATA_RATE_LIMIT: Optional[float] = None
    MARKET_DATA_RATE_BURST: Optional[int] = None
    INTL_DATA_KEY: Optional[str] = None

    BRAPI_TOKEN: Optional[str] = None
    BRAPI_BASE_URL: str = "https://brapi.dev/api"
    BRAPI_RATE_LIMIT: float = 2.0
    BRAPI_RATE_BURST: int = 5
    ALPHA_VANTAGE_API_KEY: Optional[str] = None

    LOGIN_RATE_LIMIT: str = "10/minute"
    REGISTER_RATE_LIMIT: str = "5/minute"
    DEBUG_RATE_LIMIT: str = "5/minute"

    REDIS_URL: Optional[str] = "redis://redis:6379/0"
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost:80,http://localhost"

    SUPERADMIN_EMAIL: str = "admin@sig.local"
    SUPERADMIN_PASSWORD: str = _DEFAULT_ADMIN_PASSWORD
    SUPERADMIN_NAME: str = "Super Admin"

    @model_validator(mode="after")
    def resolve_provider_compatibility(self) -> "Settings":
        quotes_token = self.QUOTES_PROVIDER_TOKEN or self.BRAPI_TOKEN
        intl_key = self.INTL_DATA_KEY or self.ALPHA_VANTAGE_API_KEY
        base_url = self.MARKET_DATA_BASE_URL or self.BRAPI_BASE_URL
        rate_limit = (
            self.MARKET_DATA_RATE_LIMIT
            if self.MARKET_DATA_RATE_LIMIT is not None
            else self.BRAPI_RATE_LIMIT
        )
        rate_burst = (
            self.MARKET_DATA_RATE_BURST
            if self.MARKET_DATA_RATE_BURST is not None
            else self.BRAPI_RATE_BURST
        )

        object.__setattr__(self, "QUOTES_PROVIDER_TOKEN", quotes_token)
        object.__setattr__(self, "BRAPI_TOKEN", quotes_token)
        object.__setattr__(self, "INTL_DATA_KEY", intl_key)
        object.__setattr__(self, "ALPHA_VANTAGE_API_KEY", intl_key)
        object.__setattr__(self, "MARKET_DATA_BASE_URL", base_url)
        object.__setattr__(self, "BRAPI_BASE_URL", base_url)
        object.__setattr__(self, "MARKET_DATA_RATE_LIMIT", rate_limit)
        object.__setattr__(self, "BRAPI_RATE_LIMIT", rate_limit)
        object.__setattr__(self, "MARKET_DATA_RATE_BURST", rate_burst)
        object.__setattr__(self, "BRAPI_RATE_BURST", rate_burst)
        return self

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        environment = info.data.get("ENVIRONMENT", "development")
        if environment == "production":
            if v == _DEFAULT_SECRET_KEY:
                raise ValueError("SECRET_KEY deve ser alterada em producao")
            if len(v) < 32:
                raise ValueError("SECRET_KEY deve ter no minimo 32 caracteres em producao")
        return v

    @field_validator("SUPERADMIN_PASSWORD")
    @classmethod
    def validate_superadmin_password(cls, v: str, info) -> str:
        environment = info.data.get("ENVIRONMENT", "development")
        if environment == "production":
            if v == _DEFAULT_ADMIN_PASSWORD:
                raise ValueError("SUPERADMIN_PASSWORD deve ser alterada em producao")
            if len(v) < 10:
                raise ValueError("SUPERADMIN_PASSWORD deve ter no minimo 10 caracteres em producao")
        return v


settings = Settings()
