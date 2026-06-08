from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    APP_DEBUG: bool = True

    # Database
    DATABASE_URL: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # BRAPI
    BRAPI_TOKEN: str
    BRAPI_BASE_URL: str = "https://brapi.dev/api"

    # Gemini
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-1.5-pro"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]

    # Cache TTL (segundos)
    CACHE_TTL_QUOTE: int = 300
    CACHE_TTL_CRYPTO: int = 120
    CACHE_TTL_CURRENCY: int = 600
    CACHE_TTL_TREASURY: int = 3600
    CACHE_TTL_MACRO: int = 21600

    class Config:
        env_file = ".env"
        case_sensitive = True

    def model_post_init(self, __context):
        # Permite CORS_ORIGINS como string JSON ou lista
        if isinstance(self.CORS_ORIGINS, str):
            self.CORS_ORIGINS = json.loads(self.CORS_ORIGINS)


settings = Settings()
