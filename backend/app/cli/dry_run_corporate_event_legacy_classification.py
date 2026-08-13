"""Emite a classificação dry-run do legado corporativo em JSON."""

from __future__ import annotations

import argparse
import asyncio
import json

from app.core.database import AsyncSessionLocal
from app.services.corporate_event_legacy_dry_run_service import (
    build_legacy_corporate_event_dry_run,
)

_SCHEMA_VERSION = "corporate-event-legacy-dry-run.v1"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classifica eventos corporativos legados sem alterar o banco."
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=20,
        help="Quantidade máxima de exemplos incluídos no JSON.",
    )
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()
    async with AsyncSessionLocal() as db:
        report = await build_legacy_corporate_event_dry_run(
            db,
            sample_limit=args.sample_limit,
        )

    payload = {
        "schema_version": _SCHEMA_VERSION,
        "dry_run": True,
        "read_only": True,
        "classification": report.to_dict(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
