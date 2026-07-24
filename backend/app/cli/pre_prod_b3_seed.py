"""CLI auditável do estágio isolado catálogo B3 + COTAHIST."""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import date

from app.services.pre_prod_b3_seed_service import (
    B3SeedAlreadyRunningError,
    run_pre_prod_b3_seed,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reconstrói somente catálogo B3 e histórico COTAHIST",
    )
    parser.add_argument("--start-year", type=int, required=True)
    parser.add_argument("--end-year", type=int, required=True)
    parser.add_argument("--cutoff-date", type=date.fromisoformat, required=True)
    return parser


async def _main() -> int:
    args = _parser().parse_args()
    try:
        result = await run_pre_prod_b3_seed(
            start_year=args.start_year,
            end_year=args.end_year,
            cutoff_date=args.cutoff_date,
        )
    except B3SeedAlreadyRunningError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    except (ValueError, RuntimeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1

    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=str))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
