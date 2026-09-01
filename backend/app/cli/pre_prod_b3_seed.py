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
        description="Reconstrói catálogo B3 e histórico COTAHIST",
    )
    parser.add_argument("--start-year", type=int, required=True)
    parser.add_argument(
        "--end-year",
        type=int,
        default=None,
        help="Ano final da janela; padrão: ano atual",
    )
    parser.add_argument(
        "--cutoff-date",
        type=date.fromisoformat,
        default=None,
        help="Data final da janela; padrão: dia atual",
    )
    parser.add_argument(
        "--history-only",
        action="store_true",
        help="Executa somente COTAHIST, sem atualizar o catálogo nacional",
    )
    return parser


async def _main() -> int:
    args = _parser().parse_args()
    today = date.today()
    end_year = args.end_year or today.year
    cutoff_date = args.cutoff_date or today
    try:
        result = await run_pre_prod_b3_seed(
            start_year=args.start_year,
            end_year=end_year,
            cutoff_date=cutoff_date,
            include_catalog=not args.history_only,
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
