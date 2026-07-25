"""CLI auditável do estágio isolado do Tesouro Direto."""
from __future__ import annotations

import argparse
import asyncio
import json

from app.core.database import AsyncSessionLocal
from app.services.pre_prod_treasury_seed_service import (
    TreasurySeedAlreadyRunningError,
    run_pre_prod_treasury_seed,
)

EXIT_OK = 0
EXIT_OPERATIONAL_FAILURE = 1
EXIT_ALREADY_RUNNING = 2
EXIT_UNEXPECTED_FAILURE = 3


def _parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        description=(
            "Sincroniza somente catálogo e histórico oficial do Tesouro Direto "
            "em uma transação auditável"
        )
    )


async def _main() -> int:
    _parser().parse_args()

    try:
        async with AsyncSessionLocal() as lock_db, AsyncSessionLocal() as work_db:
            result = await run_pre_prod_treasury_seed(
                lock_db=lock_db,
                work_db=work_db,
            )
    except TreasurySeedAlreadyRunningError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return EXIT_ALREADY_RUNNING
    except (ValueError, RuntimeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return EXIT_OPERATIONAL_FAILURE
    except Exception as exc:
        print(
            json.dumps(
                {"ok": False, "error": "falha inesperada no estágio Tesouro", "type": type(exc).__name__},
                ensure_ascii=False,
            )
        )
        return EXIT_UNEXPECTED_FAILURE

    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=str))
    return EXIT_OK if result.ok else EXIT_OPERATIONAL_FAILURE


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
