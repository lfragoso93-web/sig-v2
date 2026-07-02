from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional
import re
import os
import secrets


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

    # BRAPI
    BRAPI_TOKEN: Optional[str] = None
    BRAPI_BASE_URL: str = "https://brapi.dev/api"
    BRAPI_RATE_LIMIT: float = 2.0
    BRAPI_RATE_BURST: int = 5

    # Alpha Vantage (ativos internacionais)
    # Plano free: 25 req/min, 500 req/dia
    # Obtenha sua chave em: https://www.alphavantage.co/support/#api-key
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
    # Dividendos FIIs — bootstrap e sync via BRAPI
    # =========================================================================
    # O endpoint de dividendos de FIIs da BRAPI exige autenticação Bearer e
    # aceita no máximo 20 símbolos por chamada. O job de bootstrap roda de forma
    # assíncrona após o app subir e nunca bloqueia o deploy.
    # Escopo inicial: apenas ativos do tipo FII.
    #
    # ENABLE_DIVIDENDS_SYNC      — habilita o job de sync (default: false)
    # DIVIDENDS_BOOTSTRAP_ON_STARTUP — dispara bootstrap automático no startup
    # DIVIDENDS_BOOTSTRAP_START_DATE — data inicial para busca histórica
    # DIVIDENDS_SYNC_LOOKBACK_DAYS   — janela de tolerância no incremental
    # DIVIDENDS_BATCH_SIZE           — símbolos por request (max 20, limite BRAPI)
    ENABLE_DIVIDENDS_SYNC: bool = False
    DIVIDENDS_BOOTSTRAP_ON_STARTUP: bool = False
    DIVIDENDS_BOOTSTRAP_START_DATE: str = "2018-01-01"
    DIVIDENDS_SYNC_LOOKBACK_DAYS: int = 7
    DIVIDENDS_BATCH_SIZE: int = 20

    @field_validator("DIVIDENDS_BATCH_SIZE")
    @classmethod
    def validate_dividends_batch_size(cls, v: int) -> int:
        if v < 1:
            raise ValueError("DIVIDENDS_BATCH_SIZE deve ser >= 1")
        if v > 20:
            raise ValueError("DIVIDENDS_BATCH_SIZE deve ser <= 20 (limite BRAPI)")
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
        """Valida SECRET_KEY em produção"""
        environment = info.data.get("ENVIRONMENT", "development")
        
        if environment == "production":
            if v == "change-me-in-production":
                raise ValueError(
                    "SECRET_KEY não pode usar o valor padrão em produção! "
                    "Gere uma chave segura com: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
                )
            if len(v) < 32:
                raise ValueError(
                    "SECRET_KEY deve ter no mínimo 32 caracteres em produção"
                )
        return v

    @field_validator("SUPERADMIN_PASSWORD")
    @classmethod
    def validate_superadmin_password(cls, v: str, info) -> str:
        """Valida senha do superadmin em produção"""
        environment = info.data.get("ENVIRONMENT", "development")
        
        if environment == "production":
            if v == "Admin@1234!":
                raise ValueError(
                    "SUPERADMIN_PASSWORD não pode usar o valor padrão em produção! "
                    "Defina uma senha forte através da variável de ambiente."
                )
            if len(v) < 12:
                raise ValueError(
                    "SUPERADMIN_PASSWORD deve ter no mínimo 12 caracteres em produção"
                )
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
