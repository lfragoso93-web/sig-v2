"""Executa carga histórica corporativa controlada; dry-run é o padrão."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from datetime import UTC, date, datetime
from pathlib import Path

from app.core.database import AsyncSessionLocal
from app.services.corporate_history_load_service import run_corporate_history_load

_RUN_ID = re.compile(r"^\d{8}-\d{6}$")
_APPLY_AUTHORIZATION = "I-AUTHORIZE-CORPORATE-HISTORY"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--date-from", type=date.fromisoformat, default=date(2000, 1, 1)
    )
    parser.add_argument(
        "--date-to", type=date.fromisoformat, default=datetime.now(UTC).date()
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--authorization", default="")
    parser.add_argument("--output", type=Path)
    return parser


def _validate(arguments: argparse.Namespace) -> None:
    if not _RUN_ID.fullmatch(arguments.run_id):
        raise ValueError("run_id deve seguir YYYYMMDD-HHMMSS")
    if arguments.date_from > arguments.date_to:
        raise ValueError("date_from não pode ser posterior a date_to")
    if arguments.apply and arguments.authorization != _APPLY_AUTHORIZATION:
        raise ValueError("--apply exige --authorization I-AUTHORIZE-CORPORATE-HISTORY")


async def _run(arguments: argparse.Namespace) -> dict:
    _validate(arguments)
    async with AsyncSessionLocal() as db:
        result = await run_corporate_history_load(
            run_id=arguments.run_id,
            date_from=arguments.date_from,
            date_to=arguments.date_to,
            dry_run=not arguments.apply,
            db=db,
        )
    return result.to_dict()


def main() -> None:
    arguments = _parser().parse_args()
    try:
        payload = asyncio.run(_run(arguments))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1) from exc

    serialized = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(serialized + "\n", encoding="utf-8")
        print(arguments.output.resolve())
    else:
        print(serialized)
    raise SystemExit(0 if payload["ok"] else 1)


if __name__ == "__main__":
    main()
