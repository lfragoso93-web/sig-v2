"""Executa comparação read-only em lote para carteiras e anos com vendas."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from enum import Enum

from app.core.database import AsyncSessionLocal
from app.services.irpf_comparison_batch_service import (
    FiscalComparisonBatchReport,
    compare_discovered_targets,
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Descobre vendas e compara IRPF canônico/legado em lote.",
    )
    parser.add_argument("--start-year", type=int)
    parser.add_argument("--end-year", type=int)
    parser.add_argument(
        "--fail-on-divergence",
        action="store_true",
        help="retorna exit code 2 quando houver divergências",
    )
    return parser.parse_args()


def _json_default(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"tipo não serializável: {type(value).__name__}")


def batch_report_to_dict(report: FiscalComparisonBatchReport) -> dict[str, object]:
    comparisons = []
    for comparison in report.comparisons:
        monthly = []
        for item in comparison.monthly:
            payload = asdict(item)
            payload["kinds"] = [kind.value for kind in item.kinds]
            payload["canonical_groups"] = [
                group.value for group in item.canonical_groups
            ]
            monthly.append(payload)
        comparisons.append(
            {
                "portfolio_id": comparison.portfolio_id,
                "year": comparison.year,
                "has_divergences": comparison.has_divergences,
                "monthly": monthly,
            }
        )

    return {
        "schema_version": "irpf-canonical-legacy-batch-comparison.v1",
        "summary": {
            "targets_discovered": len(report.targets),
            "comparisons_executed": len(report.comparisons),
            "months_compared": report.months_compared,
            "matching_months": report.matching_months,
            "divergent_months": report.divergent_months,
        },
        "divergence_counts": {
            kind.value: count for kind, count in report.divergence_counts.items()
        },
        "targets": [asdict(target) for target in report.targets],
        "comparisons": comparisons,
    }


async def _main(arguments: argparse.Namespace) -> int:
    async with AsyncSessionLocal() as db:
        report = await compare_discovered_targets(
            db,
            start_year=arguments.start_year,
            end_year=arguments.end_year,
        )
        await db.rollback()

    print(
        json.dumps(
            batch_report_to_dict(report),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=_json_default,
        )
    )
    if arguments.fail_on_divergence and report.divergent_months:
        return 2
    return 0


def main() -> None:
    try:
        exit_code = asyncio.run(_main(_arguments()))
    except KeyboardInterrupt:
        exit_code = 130
    except Exception as exc:  # noqa: BLE001 - boundary operacional da CLI
        print(
            json.dumps(
                {
                    "schema_version": "irpf-canonical-legacy-batch-error.v1",
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
