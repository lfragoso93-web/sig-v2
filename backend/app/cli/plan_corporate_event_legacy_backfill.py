"""Emite o plano read-only de backfill do legado corporativo."""

from __future__ import annotations

import argparse
import asyncio
import json

from app.core.database import AsyncSessionLocal
from app.services.corporate_event_legacy_backfill_plan_service import (
    build_legacy_corporate_event_backfill_plan,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gera um plano read-only para o legado de eventos corporativos.",
    )
    parser.add_argument(
        "--entry-limit",
        type=int,
        default=100,
        help="Quantidade máxima de entradas incluídas no artefato JSON.",
    )
    return parser


async def main() -> None:
    args = _parser().parse_args()
    async with AsyncSessionLocal() as db:
        plan = await build_legacy_corporate_event_backfill_plan(
            db,
            entry_limit=args.entry_limit,
        )

    payload = {
        "schema_version": "corporate-event-legacy-backfill-plan.v1",
        "dry_run": True,
        "read_only": True,
        "writes_executed": False,
        "plan": plan.to_dict(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
