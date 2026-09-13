"""Remove duplicatas Tesouro vazias e explicitamente certificadas."""
from __future__ import annotations

import argparse
import asyncio
import json

from app.core.database import AsyncSessionLocal
from app.services.treasury_empty_duplicate_cleanup_service import (
    cleanup_empty_treasury_duplicate_assets,
)


async def _main(*, execute: bool) -> None:
    async with AsyncSessionLocal() as db:
        result = await cleanup_empty_treasury_duplicate_assets(
            db,
            dry_run=not execute,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Executa o delete após a auditoria protegida.",
    )
    arguments = parser.parse_args()
    asyncio.run(_main(execute=arguments.execute))


if __name__ == "__main__":
    main()
