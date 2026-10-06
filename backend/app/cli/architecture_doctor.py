"""CLI read-only dos gates estáticos do Architecture Doctor."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.doctor.catalog import architecture_check_by_id
from app.doctor.contracts import DoctorCheckKind
from app.doctor.static_runner import StaticDoctorReport, run_static_checks


REPORT_SCHEMA_VERSION = "architecture-doctor.v1"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
STATIC_FINDING_IDS = tuple(
    finding_id
    for finding_id, entry in architecture_check_by_id.items()
    if entry.kind is DoctorCheckKind.STATIC
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument(
        "--check",
        action="append",
        choices=STATIC_FINDING_IDS,
        dest="finding_ids",
        help="ID estático; pode ser repetido para selecionar mais de um",
    )
    selection.add_argument(
        "--all-static",
        action="store_true",
        help="executa todos os IDs classificados como static",
    )
    parser.add_argument(
        "--format",
        choices=("human", "json"),
        default="human",
        dest="output_format",
    )
    return parser


def _payload(report: StaticDoctorReport) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "mode": "static",
        "exit_code": int(report.exit_code),
        "results": [
            {
                "finding_id": result.finding_id,
                "title": architecture_check_by_id[result.finding_id].title,
                "severity": architecture_check_by_id[result.finding_id].severity.value,
                "status": result.status.value,
                "detail": result.detail,
            }
            for result in report.results
        ],
    }


def _print_human(report: StaticDoctorReport) -> None:
    for result in report.results:
        title = architecture_check_by_id[result.finding_id].title
        print(f"[{result.status.value.upper()}] {result.finding_id} {title}")
        print(f"  {result.detail}")
    print(f"Architecture Doctor exit_code={int(report.exit_code)}")


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    finding_ids = (
        STATIC_FINDING_IDS if arguments.all_static else tuple(arguments.finding_ids)
    )
    report = run_static_checks(finding_ids, repository_root=REPOSITORY_ROOT)

    if arguments.output_format == "json":
        print(json.dumps(_payload(report), ensure_ascii=False, indent=2))
    else:
        _print_human(report)
    return int(report.exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
