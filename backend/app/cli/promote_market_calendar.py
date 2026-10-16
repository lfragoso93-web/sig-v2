"""Dry-run-first promotion of a reviewed market-calendar candidate."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Sequence
from pathlib import Path

from app.core.database import AsyncSessionLocal
from app.services.market_calendar_promotion_executor import (
    execute_market_calendar_promotion,
    prepare_market_calendar_promotion,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_file", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirmation")
    return parser


async def _main(arguments: argparse.Namespace) -> int:
    if arguments.execute != bool(arguments.confirmation):
        raise ValueError("--execute requires --confirmation and vice-versa")
    candidate = json.loads(arguments.candidate_file.read_text(encoding="utf-8"))
    if not isinstance(candidate, dict):
        raise ValueError("market calendar candidate must be an object")

    async with AsyncSessionLocal() as session:
        try:
            if arguments.execute:
                result = await execute_market_calendar_promotion(
                    session,
                    candidate=candidate,
                    confirmation=arguments.confirmation,
                )
                await session.commit()
                payload = {
                    "mode": "execute",
                    "database_writes_executed": result.database_writes_executed,
                    "transaction_committed": True,
                    "result": result.to_dict(),
                }
            else:
                preflight = await prepare_market_calendar_promotion(
                    session,
                    candidate=candidate,
                )
                await session.rollback()
                payload = {
                    "mode": "dry-run",
                    "database_writes_executed": 0,
                    "transaction_committed": False,
                    "preflight": preflight.to_dict(),
                }
        except Exception:
            await session.rollback()
            raise
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def main(argv: Sequence[str] | None = None) -> None:
    raise SystemExit(asyncio.run(_main(_parser().parse_args(argv))))


if __name__ == "__main__":
    main()
