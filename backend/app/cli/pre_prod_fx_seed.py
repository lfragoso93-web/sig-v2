"""CLI auditável do estágio isolado de câmbio."""
from __future__ import annotations

import argparse
import asyncio
import json

from app.core.database import AsyncSessionLocal
from app.services.pre_prod_fx_seed_contract import (
    FX_SEED_BRANCH,
    validate_fx_seed_identity,
)
from app.services.pre_prod_fx_seed_preparation import FxSeedPreparationError
from app.services.pre_prod_fx_seed_service import (
    FxSeedAlreadyRunningError,
    run_pre_prod_fx_seed,
)

EXIT_OK = 0
EXIT_OPERATIONAL_FAILURE = 1
EXIT_ALREADY_RUNNING = 2
EXIT_UNEXPECTED_FAILURE = 3


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Sincroniza exclusivamente a série cambial canônica USD-BRL "
            "com PTAX de venda do BCB em uma transação auditável"
        )
    )
    parser.add_argument("--run-id", required=True, help="Identidade YYYYMMDD-HHMMSS")
    parser.add_argument(
        "--branch",
        required=True,
        help=f"Branch operacional obrigatória ({FX_SEED_BRANCH})",
    )
    parser.add_argument(
        "--commit-sha",
        required=True,
        help="SHA Git completo, hexadecimal minúsculo de 40 caracteres",
    )
    parser.add_argument(
        "--start-date",
        required=True,
        help="Data inicial inclusiva no formato YYYY-MM-DD",
    )
    parser.add_argument(
        "--end-date",
        required=True,
        help="Data final inclusiva no formato YYYY-MM-DD",
    )
    return parser


async def _main() -> int:
    args = _parser().parse_args()

    try:
        validate_fx_seed_identity(
            run_id=args.run_id,
            branch=args.branch,
            commit_sha=args.commit_sha,
        )
        async with AsyncSessionLocal() as lock_db, AsyncSessionLocal() as work_db:
            result = await run_pre_prod_fx_seed(
                run_id=args.run_id,
                branch=args.branch,
                commit_sha=args.commit_sha,
                start_date=args.start_date,
                end_date=args.end_date,
                lock_db=lock_db,
                work_db=work_db,
            )
    except FxSeedAlreadyRunningError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return EXIT_ALREADY_RUNNING
    except (ValueError, RuntimeError, FxSeedPreparationError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return EXIT_OPERATIONAL_FAILURE
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "falha inesperada no estágio cambial",
                    "type": type(exc).__name__,
                },
                ensure_ascii=False,
            )
        )
        return EXIT_UNEXPECTED_FAILURE

    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=str))
    return EXIT_OK if result.ok else EXIT_OPERATIONAL_FAILURE


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
