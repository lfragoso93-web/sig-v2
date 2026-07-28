"""CLI auditável do estágio isolado de proventos."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import date

import httpx

from app.core.database import AsyncSessionLocal
from app.services.pre_prod_dividends_seed_collector import (
    StrictDividendCollectionError,
)
from app.services.pre_prod_dividends_seed_contract import (
    DIVIDENDS_SEED_BRANCH,
    DividendsSeedContractError,
    validate_dividends_seed_identity,
)
from app.services.pre_prod_dividends_seed_materialization import (
    DividendsSeedMaterializationError,
)
from app.services.pre_prod_dividends_seed_persistence import (
    DividendsSeedAlreadyRunningError,
    DividendsSeedPersistenceError,
)
from app.services.pre_prod_dividends_seed_providers import (
    StrictBrapiDividendProvider,
    StrictYahooDividendProvider,
    fetch_yahoo_dividend_history,
)
from app.services.pre_prod_dividends_seed_service import (
    DividendsSeedUnexpectedStageError,
    run_pre_prod_dividends_seed,
)

EXIT_OK = 0
EXIT_OPERATIONAL_FAILURE = 1
EXIT_ALREADY_RUNNING = 2
EXIT_UNEXPECTED_FAILURE = 3


def _sqlstate(exc: BaseException) -> str | None:
    current: BaseException | None = exc
    visited: set[int] = set()
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        value = getattr(current, "sqlstate", None)
        if value:
            return str(value)
        current = current.__cause__ or current.__context__
    return None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Reconstrói somente o catálogo global e os direitos por carteira "
            "de proventos em uma transação auditável"
        )
    )
    parser.add_argument("--run-id", required=True, help="Identidade YYYYMMDD-HHMMSS")
    parser.add_argument(
        "--branch",
        required=True,
        help=f"Branch operacional obrigatória ({DIVIDENDS_SEED_BRANCH})",
    )
    parser.add_argument(
        "--commit-sha",
        required=True,
        help="SHA Git completo, hexadecimal minúsculo de 40 caracteres",
    )
    parser.add_argument("--start-date", required=True, help="Data inicial YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="Data final YYYY-MM-DD")
    return parser


async def _main() -> int:
    args = _parser().parse_args()

    try:
        validate_dividends_seed_identity(
            run_id=args.run_id,
            branch=args.branch,
            commit_sha=args.commit_sha,
        )
        start_date = date.fromisoformat(args.start_date)
        end_date = date.fromisoformat(args.end_date)
        if start_date > end_date:
            raise DividendsSeedContractError(
                "start_date não pode ser posterior a end_date"
            )

        async with (
            AsyncSessionLocal() as db,
            httpx.AsyncClient(timeout=30.0) as client,
        ):
            result = await run_pre_prod_dividends_seed(
                run_id=args.run_id,
                branch=args.branch,
                commit_sha=args.commit_sha,
                start_date=start_date,
                end_date=end_date,
                db=db,
                providers=(
                    StrictBrapiDividendProvider(client=client),
                    StrictYahooDividendProvider(
                        history_fetcher=fetch_yahoo_dividend_history
                    ),
                ),
            )
    except DividendsSeedAlreadyRunningError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return EXIT_ALREADY_RUNNING
    except (
        DividendsSeedContractError,
        StrictDividendCollectionError,
        DividendsSeedPersistenceError,
        DividendsSeedMaterializationError,
        ValueError,
    ) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return EXIT_OPERATIONAL_FAILURE
    except Exception as exc:  # noqa: BLE001
        stage = (
            exc.stage
            if isinstance(exc, DividendsSeedUnexpectedStageError)
            else "cli"
        )
        root_cause = exc.__cause__ or exc
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "falha inesperada no estágio de proventos",
                    "stage": stage,
                    "type": type(root_cause).__name__,
                    "sqlstate": _sqlstate(exc),
                },
                ensure_ascii=False,
            )
        )
        return EXIT_UNEXPECTED_FAILURE

    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=str))
    return EXIT_OK if result.ok else EXIT_OPERATIONAL_FAILURE


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
