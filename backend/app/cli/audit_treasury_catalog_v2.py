"""CLI para auditar transacoes e assets contra o catalogo oficial do Tesouro."""
from __future__ import annotations

import argparse
import asyncio
import json

from app.core.database import AsyncSessionLocal
from app.services.treasury_catalog_v2_audit_service import audit_treasury_catalog_v2


async def _main() -> None:
    async with AsyncSessionLocal() as db:
        result = await audit_treasury_catalog_v2(db)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    asyncio.run(_main())


if __name__ == "__main__":
    main()
