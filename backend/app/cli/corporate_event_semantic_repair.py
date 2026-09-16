"""Emite plano dry-run-first para reparo semantico de eventos corporativos.

Uso dentro do container backend:
    python -m app.cli.corporate_event_semantic_repair --event-id 370
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from app.core.database import AsyncSessionLocal
from app.services.corporate_event_semantic_repair import (
    build_corporate_event_semantic_repair_dry_run,
    execute_corporate_event_semantic_repair,
)


def _configure_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="strict")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Gera um plano dry-run-first para reparar identidade semantica "
            "historica de eventos corporativos BRAPI."
        )
    )
    parser.add_argument("--event-id", type=int, action="append", required=True)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Persiste somente event_type, source_event_id e source_payload_hash.",
    )
    return parser.parse_args()


async def _main(arguments: argparse.Namespace) -> int:
    event_ids = tuple(arguments.event_id)
    async with AsyncSessionLocal() as db:
        if arguments.execute:
            report = await execute_corporate_event_semantic_repair(
                db,
                event_ids=event_ids,
            )
            await db.commit()
        else:
            report = await build_corporate_event_semantic_repair_dry_run(
                db,
                event_ids=event_ids,
            )
            await db.rollback()

    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def main() -> None:
    _configure_output()
    try:
        exit_code = asyncio.run(_main(_arguments()))
    except KeyboardInterrupt:
        exit_code = 130
    except Exception as exc:  # noqa: BLE001 - boundary operacional da CLI
        print(
            json.dumps(
                {
                    "schema_version": "corporate-event-semantic-repair-error.v1",
                    "ok": False,
                    "error": str(exc),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        exit_code = 1
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
