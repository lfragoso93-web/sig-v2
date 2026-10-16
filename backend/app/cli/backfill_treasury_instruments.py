"""Planeja o backfill da tabela treasury_instruments; escrita exige --execute."""
from __future__ import annotations

import argparse
import asyncio
import json

from app.core.database import AsyncSessionLocal
from app.services.treasury_instrument_backfill_service import (
    backfill_treasury_instruments,
)


async def _main(*, execute: bool) -> None:
    async with AsyncSessionLocal() as db:
        report = await backfill_treasury_instruments(
            db,
            dry_run=not execute,
        )
        if not execute:
            await db.rollback()
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Insere apenas candidatos do plano; sem a flag, faz dry-run.",
    )
    arguments = parser.parse_args()
    asyncio.run(_main(execute=arguments.execute))


if __name__ == "__main__":
    main()
