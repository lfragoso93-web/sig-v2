import logging
import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log_safety import sanitize_log_value
from app.integrations.b3_market_calendar import validate_b3_source_url
from app.models.system_config import SystemConfig

logger = logging.getLogger(__name__)

_B3_CALENDAR_SOURCE_URL_KEY = "market_calendar.b3_source_url"
_B3_CALENDAR_SOURCE_YEAR_KEY = "market_calendar.b3_source_year"


def validate_system_config_value(key: str, value: str) -> None:
    """Validate narrowly scoped SuperAdmin calendar settings before persistence."""
    normalized = value.strip()
    if key == _B3_CALENDAR_SOURCE_URL_KEY and normalized:
        validate_b3_source_url(normalized)
    if key == _B3_CALENDAR_SOURCE_YEAR_KEY and normalized:
        if not re.fullmatch(r"20\d{2}", normalized):
            raise ValueError("B3 calendar source year must be a four-digit year")


async def get_config(db: AsyncSession, key: str) -> str | None:
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    cfg = result.scalar_one_or_none()
    return cfg.value if cfg else None


async def get_bool_config(db: AsyncSession, key: str, default: bool = False) -> bool:
    val = await get_config(db, key)
    if val is None:
        return default
    return val.lower() in ("true", "1", "yes")


async def set_config(db: AsyncSession, key: str, value: str) -> None:
    validate_system_config_value(key, value)
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    cfg = result.scalar_one_or_none()
    if cfg:
        cfg.value = value
        cfg.updated_at = datetime.now(timezone.utc)
    else:
        cfg = SystemConfig(key=key, value=value)
        db.add(cfg)
    await db.commit()


async def get_all_configs(
    db: AsyncSession,
    public_only: bool = True,
) -> list[SystemConfig]:
    """Lista todas as configurações; opcionalmente somente as públicas."""
    query = select(SystemConfig)
    if public_only:
        query = query.where(SystemConfig.is_public == True)  # noqa: E712
    query = query.order_by(SystemConfig.key)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_config(
    db: AsyncSession,
    key: str,
    value: str,
) -> SystemConfig:
    """Faz upsert de uma configuração por chave e retorna o registro atualizado."""
    validate_system_config_value(key, value)
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    cfg = result.scalar_one_or_none()
    if cfg:
        cfg.value = value
        cfg.updated_at = datetime.now(timezone.utc)
    else:
        cfg = SystemConfig(key=key, value=value)
        db.add(cfg)
    await db.commit()
    await db.refresh(cfg)
    logger.info(
        "[ConfigService] Config atualizada: %s=%s",
        sanitize_log_value(key),
        sanitize_log_value(value),
    )
    return cfg


async def bulk_update_configs(
    db: AsyncSession,
    configs: dict[str, str],
) -> list[SystemConfig]:
    """Atualiza múltiplas configurações em um único commit."""
    for key, value in configs.items():
        validate_system_config_value(key, value)
    updated: list[SystemConfig] = []
    for key, value in configs.items():
        result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
        cfg = result.scalar_one_or_none()
        if cfg:
            cfg.value = value
            cfg.updated_at = datetime.now(timezone.utc)
        else:
            cfg = SystemConfig(key=key, value=value)
            db.add(cfg)
        updated.append(cfg)
    await db.commit()
    for cfg in updated:
        await db.refresh(cfg)
    logger.info("[ConfigService] Bulk update: %s configs atualizadas", len(updated))
    return updated
