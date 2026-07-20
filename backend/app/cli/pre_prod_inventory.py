"""Gera o inventário read-only da base antes do rebuild pré-produção.

Uso dentro do container backend:
    python -m app.cli.pre_prod_inventory
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys

from app.services.pre_prod_inventory_service import build_pre_prod_inventory


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def _configure_utf8_output() -> None:
    """Padroniza stdout/stderr em UTF-8, inclusive quando consumidos pelo PowerShell."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="strict")


async def _main() -> int:
    report = await build_pre_prod_inventory()
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    has_blockers = bool(
        report.totals["blocking_findings"]
        or report.totals["unclassified_tables"]
    )
    return 1 if has_blockers else 0


def main() -> None:
    _configure_utf8_output()
    _configure_logging()
    try:
        exit_code = asyncio.run(_main())
    except KeyboardInterrupt:
        logging.getLogger(__name__).warning("inventário pré-produção interrompido")
        exit_code = 130
    except Exception:
        logging.getLogger(__name__).exception(
            "inventário pré-produção falhou antes do relatório final"
        )
        exit_code = 1
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
