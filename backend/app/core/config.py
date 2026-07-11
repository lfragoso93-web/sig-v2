from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator
from typing import Optional
import re


class Settings(BaseSettings):
    # Banco de dados
    DATABASE_URL: str = "postgresql://sgi:sgi@db:5432/sgi"
    ASYNC_DATABASE_URL: str = "postgresql+asyncpg://sgi:sgi@db:5432/sgi"

    # Debug
    APP_DEBUG: bool = False

    # Environment
    ENVIRONMENT: str = "development"

    # JWT
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Provedor principal de dados de mercado
    QUOTES_PROVIDER_TOKEN: Optional[str] = None
    MARKET_DATA_BASE_URL: str = "https://brapi.dev/api"
    MARKET_DATA_RATE_LIMIT: float = 2.0
    MARKET_DATA_RATE_BURST: int = 5

    # Fonte complementar de dados internacionais
    INTL_DATA_KEY: Optional[str] = None

    # Compatibilidade temporaria com instalacoes anteriores.
    # Os modulos internos ainda podem consumir estes atributos durante a migracao.
    BRAPI_TOKEN: Optional[str] = None
    BRAPI_BASE_URL: Optional[str] = None
    BRAPI_RATE_LIMIT: Optional[float] = None
    BRAPI_RATE_BURST: Optional[int] = None
    ALPHA_VANTAGE_API_KEY: Optional[str] = None

    # Rate limiting de endpoints publicos (slowapi)
    LOGIN_RATE_LIMIT: str = "10/minute"
    REGISTER_RATE_LIMIT: str = "5/minute"

    # Rate limiting do router de debug
    DEBUG_RATE_LIMIT: str = "5/minute"

    # Redis (opcional)
    REDIS_URL: Optional[str] = "redis://redis:6379/0"
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost:80,http://localhost"

    # Superadmin seed
    SUPERADMIN_EMAIL: str = "admin@sig.local"
    SUPERADMIN_PASSWORD: str = "Admin@1234!"
    SUPERADMIN_NAME: str = "Super Admin"

    # =========================================================================
    # Dividendos FIIs — bootstrap e sync por provedor de dados
    # =========================================================================
    # O endpoint de dividendos exige autenticacao e aceita no maximo
    # 20 simbolos por chamada. O job de bootstrap roda de forma assincrona
    # apos o app subir e nunca bloqueia o deploy.
    # Escopo inicial: apenas ativos do tipo FII.
    #
    # ENABLE_DIVIDENDS_SYNC          — habilita o job de sync (default: false)
    # DIVIDENDS_BOOTSTRAP_ON_STARTUP — dispara bootstrap automatico no startup
    # DIVIDENDS_BOOTSTRAP_START_DATE — data inicial para busca historica
    # DIVIDENDS_SYNC_LOOKBACK_DAYS   — janela de tolerancia no incremental
    # DIVIDENDS_BATCH_SIZE           — simbolos por request (max 20)
    ENABLE_DIVIDENDS_SYNC: bool = False
    DIVIDENDS_BOOTSTRAP_ON_STARTUP: bool = False
    DIVIDENDS_BOOTSTRAP_START_DATE: str = "2018-01-01"
    DIVIDENDS_SYNC_LOOKBACK_DAYS: int = 7
    DIVIDENDS_BATCH_SIZE: int = 20

    @model_validator(mode="after")
    def resolve_provider_compatibility(self):
        """Resolve nomes genericos e legados sem quebrar ambientes existentes."""
        quotes_token = self.QUOTES_PROVIDER_TOKEN or self.BRAPI_TOKEN
        intl_key = self.INTL_DATA_KEY or self.ALPHA_VANTAGE_API_KEY
        base_url = self.BRAPI_BASE_URL or self.MARKET_DATA_BASE_URL
        rate_limit = self.BRAPI_RATE_LIMIT if self.BRAPI_RATE_LIMIT is not None else self.MARKET_DATA_RATE_LIMIT
        rate_burst = self.BRAPI_RATE_BURST if self.BRAPI_RATE_BURST is not None else self.MARKET_DATA_RATE_BURST

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

    @field_validator("DIVIDENDS_BATCH_SIZE")
    @classmethod
    def validate_dividends_batch_size(cls, v: int) -> int:
        if v < 1:
            raise ValueError("DIVIDENDS_BATCH_SIZE deve ser >= 1")
        if v > 20:
            raise ValueError("DIVIDENDS_BATCH_SIZE deve ser <= 20")
        return v

    @field_validator("DIVIDENDS_SYNC_LOOKBACK_DAYS")
    @classmethod
    def validate_dividends_sync_lookback_days(cls, v: int) -> int:
        if v < 0:
            raise ValueError("DIVIDENDS_SYNC_LOOKBACK_DAYS deve ser >= 0")
        return v

    @field_validator("DIVIDENDS_BOOTSTRAP_START_DATE")
    @classmethod
    def validate_dividends_bootstrap_start_date(cls, v: str) -> str:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError(
                "DIVIDENDS_BOOTSTRAP_START_DATE deve estar no formato YYYY-MM-DD"
            )
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """Valida SECRET_KEY em producao."""
        environment = info.data.get("ENVIRONMENT", "development")

        if environment == "production":
            if v == "change-me-in-production":
                raise ValueError(
                    "SECRET_KEY nao pode usar o valor padrao em producao! "
                    "Gere uma chave segura com: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
                )
            if len(v) < 32:
                raise ValueError(
                    "SECRET_KEY deve ter no minimo 32 caracteres em producao"
                )
        return v

    @field_validator("SUPERADMIN_PASSWORD")
    @classmethod
    def validate_superadmin_password(cls, v: str, info) -> str:
        """Valida senha do superadmin em producao."""
        environment = info.data.get("ENVIRONMENT", "development")

        if environment == "production":
            if v == "Admin@1234!":
                raise ValueError(
                    "SUPERADMIN_PASSWORD nao pode usar o valor padrao em producao! "
                    "Defina uma senha forte atraves da variavel de ambiente."
                )
            if len(v) < 10:
                raise ValueError(
                    "SUPERADMIN_PASSWORD deve ter no minimo 10 caracteres em producao"
                )
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
