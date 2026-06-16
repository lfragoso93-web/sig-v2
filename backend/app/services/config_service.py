import logging
from datetime import datetime, timezone
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
        cfg.updated_at = datetime.now(timezone.utc)
    else:
        cfg = AppConfig(key=key, value=value)
        db.add(cfg)
    await db.commit()


async def get_all_configs(
    db: AsyncSession,
    public_only: bool = True,
) -> list[AppConfig]:
    """Lista todas as configuracoes. Se public_only=True, retorna apenas is_public=True."""
    query = select(AppConfig)
    if public_only:
        query = query.where(AppConfig.is_public == True)  # noqa: E712
    query = query.order_by(AppConfig.key)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_config(
    db: AsyncSession,
    key: str,
    value: str,
) -> AppConfig:
    """Upsert de uma configuracao pelo key. Retorna o objeto atualizado."""
    result = await db.execute(select(AppConfig).where(AppConfig.key == key))
    cfg = result.scalar_one_or_none()
    if cfg:
        cfg.value = value
        cfg.updated_at = datetime.now(timezone.utc)
    else:
        cfg = AppConfig(key=key, value=value)
        db.add(cfg)
    await db.commit()
    await db.refresh(cfg)
    logger.info(f"[ConfigService] Config atualizada: {key}={value}")
    return cfg


async def bulk_update_configs(
    db: AsyncSession,
    configs: dict[str, str],
) -> list[AppConfig]:
    """Atualiza multiplas configuracoes em um unico commit."""
    updated = []
    for key, value in configs.items():
        result = await db.execute(select(AppConfig).where(AppConfig.key == key))
        cfg = result.scalar_one_or_none()
        if cfg:
            cfg.value = value
            cfg.updated_at = datetime.now(timezone.utc)
        else:
            cfg = AppConfig(key=key, value=value)
            db.add(cfg)
        updated.append(cfg)
    await db.commit()
    for cfg in updated:
        await db.refresh(cfg)
    logger.info(f"[ConfigService] Bulk update: {len(updated)} configs atualizadas")
    return updated
