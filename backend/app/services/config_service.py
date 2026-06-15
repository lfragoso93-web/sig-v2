import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.config import AppConfig

logger = logging.getLogger(__name__)


async def get_config(db: AsyncSession, key: str) -> str | None:
    result = await db.execute(select(AppConfig).where(AppConfig.key == key))
    cfg = result.scalar_one_or_none()
    return cfg.value if cfg else None


async def get_bool_config(db: AsyncSession, key: str, default: bool = False) -> bool:
    val = await get_config(db, key)
    if val is None:
        return default
    return val.lower() in ("true", "1", "yes")


async def set_config(db: AsyncSession, key: str, value: str) -> None:
    result = await db.execute(select(AppConfig).where(AppConfig.key == key))
    cfg = result.scalar_one_or_none()
    if cfg:
        cfg.value = value
    else:
        cfg = AppConfig(key=key, value=value)
        db.add(cfg)
    await db.commit()
