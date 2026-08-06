"""CLI offline para comparar relatórios do bootstrap canônico de ativos."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.services.asset_bootstrap_report_diff_service import (
    compare_asset_bootstrap_reports,
)


def _load_report(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("report payload must be an object")

    nested_report = payload.get("report")
    if nested_report is None:
        return payload
    if not isinstance(nested_report, dict):
        raise ValueError("report envelope entry must be an object")
    return nested_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    args = parser.parse_args()

    before = _load_report(args.before)
    after = _load_report(args.after)
    diff = compare_asset_bootstrap_reports(before, after)
    print(
        json.dumps(
            {
                "schema_version": "asset-bootstrap-report-diff.v1",
                "offline": True,
                "read_only": True,
                "diff": diff.to_dict(),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if diff.equivalent else 1


if __name__ == "__main__":
    raise SystemExit(main())
