from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from app.models.system_config import SystemConfig
from typing import Optional


async def get_all_configs(db: AsyncSession, public_only: bool = False) -> list[SystemConfig]:
    query = select(SystemConfig)
    if public_only:
        query = query.where(SystemConfig.is_public == True)
    result = await db.execute(query.order_by(SystemConfig.key))
    return result.scalars().all()


async def get_config(db: AsyncSession, key: str) -> Optional[SystemConfig]:
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    return result.scalar_one_or_none()


async def update_config(db: AsyncSession, key: str, value: str) -> SystemConfig:
    config = await get_config(db, key)
    if not config:
        raise HTTPException(status_code=404, detail=f"Configuração '{key}' não encontrada")
    config.value = value
    await db.flush()
    await db.refresh(config)
    return config


async def bulk_update_configs(db: AsyncSession, configs: dict[str, str]) -> list[SystemConfig]:
    updated = []
    for key, value in configs.items():
        config = await get_config(db, key)
        if config:
            config.value = value
            await db.flush()
            await db.refresh(config)
            updated.append(config)
    return updated
