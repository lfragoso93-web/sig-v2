from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Banco de dados
    DATABASE_URL: str = "postgresql://sgi:sgi@db:5432/sgi"
    ASYNC_DATABASE_URL: str = "postgresql+asyncpg://sgi:sgi@db:5432/sgi"

    # Debug
    APP_DEBUG: bool = False

    # JWT
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # BRAPI
    BRAPI_TOKEN: Optional[str] = None
    BRAPI_BASE_URL: str = "https://brapi.dev/api"

    # Redis (opcional)
    REDIS_URL: Optional[str] = "redis://redis:6379/0"
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost:80,http://localhost"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
