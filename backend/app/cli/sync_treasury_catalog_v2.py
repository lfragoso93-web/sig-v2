"""CLI para sincronizar o Catalog v2 oficial do Tesouro."""
from __future__ import annotations

import asyncio
import json

from app.core.database import AsyncSessionLocal
from app.services.treasury_catalog_v2_service import sync_treasury_catalog_v2


async def _main() -> None:
    async with AsyncSessionLocal() as db:
        result = await sync_treasury_catalog_v2(db)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(_main())
