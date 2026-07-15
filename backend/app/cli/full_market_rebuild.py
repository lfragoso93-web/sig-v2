"""Executa a manutencao completa da base canonica de mercado.

Uso dentro do container backend:
    python -m app.cli.full_market_rebuild
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys

from app.services.full_market_rebuild_canonical_service import run_full_market_rebuild


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


async def _main() -> int:
    summary = await run_full_market_rebuild()
    print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
    return 0 if summary.ok else 1


def main() -> None:
    _configure_logging()
    try:
        exit_code = asyncio.run(_main())
    except KeyboardInterrupt:
        logging.getLogger(__name__).warning("full_market_rebuild interrompido pelo usuario")
        exit_code = 130
    except Exception:
        logging.getLogger(__name__).exception("full_market_rebuild falhou antes do resumo final")
        exit_code = 1
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
