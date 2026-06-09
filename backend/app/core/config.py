from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Banco de dados
    DATABASE_URL: str = "postgresql://sig:sig@db:5432/sig"

    # Debug
    APP_DEBUG: bool = False

    # JWT
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str  = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h

    # BRAPI
    BRAPI_TOKEN: Optional[str] = None

    # Redis (opcional, para cache de cotacoes)
    REDIS_URL: Optional[str] = "redis://redis:6379/0"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
