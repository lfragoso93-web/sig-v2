"""Executa auditoria não destrutiva dos aliases do Tesouro Direto."""
from __future__ import annotations

import asyncio
import json

from app.core.database import AsyncSessionLocal
from app.services.treasury_canonical_audit_service import audit_treasury_canonical_assets


async def main() -> None:
    async with AsyncSessionLocal() as db:
        result = await audit_treasury_canonical_assets(db)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
