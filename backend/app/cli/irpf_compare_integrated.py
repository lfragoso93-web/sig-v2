"""Executa comparação read-only da apuração integrada canônica com o legado.

Uso dentro do container backend:
    python -m app.cli.irpf_compare_integrated --portfolio-id 1 --year 2024
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from decimal import Decimal
from enum import Enum

from app.core.database import AsyncSessionLocal
from app.services.irpf_integrated_comparison_service import (
    compare_annual_integrated_with_legacy,
)
from app.services.irpf_integrated_legacy_comparison import (
    IntegratedFiscalAnnualComparison,
)


def _configure_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="strict")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compara a apuração integrada canônica de Swing e Day Trade com o "
            "motor fiscal legado sem alterar dados ou consumidores."
        )
    )
    parser.add_argument("--portfolio-id", type=int, required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument(
        "--fail-on-divergence",
        action="store_true",
        help="retorna exit code 2 quando houver qualquer divergência",
    )
    return parser.parse_args()


def _json_default(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"tipo não serializável: {type(value).__name__}")


def comparison_to_dict(
    comparison: IntegratedFiscalAnnualComparison,
) -> dict[str, object]:
    monthly = []
    classification_counts: dict[str, int] = {}
    for item in comparison.monthly:
        payload = asdict(item)
        payload["kinds"] = [kind.value for kind in item.kinds]
        monthly.append(payload)
        for kind in item.kinds:
            classification_counts[kind.value] = (
                classification_counts.get(kind.value, 0) + 1
            )

    divergent_months = sum(1 for item in comparison.monthly if not item.matches)
    return {
        "schema_version": "irpf-integrated-canonical-legacy-comparison.v1",
        "portfolio_id": comparison.portfolio_id,
        "year": comparison.year,
        "has_divergences": comparison.has_divergences,
        "summary": {
            "months_compared": len(comparison.monthly),
            "matching_months": len(comparison.monthly) - divergent_months,
            "divergent_months": divergent_months,
            "classification_counts": dict(sorted(classification_counts.items())),
        },
        "monthly": monthly,
    }


async def _main(arguments: argparse.Namespace) -> int:
    if arguments.portfolio_id <= 0:
        raise ValueError("portfolio-id deve ser positivo")
    if arguments.year < 1900 or arguments.year > 9999:
        raise ValueError("ano fiscal inválido")

    async with AsyncSessionLocal() as db:
        comparison = await compare_annual_integrated_with_legacy(
            db,
            portfolio_id=arguments.portfolio_id,
            year=arguments.year,
        )
        await db.rollback()

    print(
        json.dumps(
            comparison_to_dict(comparison),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=_json_default,
        )
    )
    if arguments.fail_on_divergence and comparison.has_divergences:
        return 2
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
                    "schema_version": "irpf-integrated-comparison-error.v1",
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
