"""Emite a apuração anual canônica versionada em JSON.

Uso dentro do container backend:
    python -m app.cli.irpf_annual_assessment --portfolio-id 1 --year 2024
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from decimal import Decimal
from enum import Enum

from app.core.database import AsyncSessionLocal
from app.services.irpf_annual_assessment_service import (
    build_irpf_annual_assessment,
)


def _configure_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="strict")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Emite o contrato interno versionado da apuração anual canônica "
            "de IRPF sem alterar dados."
        )
    )
    parser.add_argument("--portfolio-id", type=int, required=True)
    parser.add_argument("--year", type=int, required=True)
    return parser.parse_args()


def _json_default(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"tipo não serializável: {type(value).__name__}")


async def _main(arguments: argparse.Namespace) -> int:
    if arguments.portfolio_id <= 0:
        raise ValueError("portfolio-id deve ser positivo")
    if arguments.year < 1900 or arguments.year > 9999:
        raise ValueError("ano fiscal inválido")

    async with AsyncSessionLocal() as db:
        contract = await build_irpf_annual_assessment(
            db,
            portfolio_id=arguments.portfolio_id,
            year=arguments.year,
        )
        await db.rollback()

    print(
        json.dumps(
            contract.to_dict(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=_json_default,
        )
    )
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
                    "schema_version": "irpf-annual-assessment-error.v1",
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
