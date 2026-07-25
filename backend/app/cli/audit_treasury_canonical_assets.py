"""Executa auditoria não destrutiva dos aliases do Tesouro Direto."""
from __future__ import annotations

import argparse
import asyncio
import json

from app.core.database import AsyncSessionLocal
from app.services.treasury_canonical_audit_service import audit_treasury_canonical_assets


async def _main() -> None:
    async with AsyncSessionLocal() as db:
        result = await audit_treasury_canonical_assets(db)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    asyncio.run(_main())


if __name__ == "__main__":
    main()
