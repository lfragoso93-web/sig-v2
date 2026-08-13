"""Compara dois artefatos JSON de plano de backfill corporativo."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.services.corporate_event_backfill_plan_diff_service import (
    compare_corporate_event_backfill_plans,
)


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"artefato inválido: {path}")
    plan = payload.get("plan", payload)
    if not isinstance(plan, dict):
        raise ValueError(f"plano inválido: {path}")
    return plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    args = parser.parse_args()

    diff = compare_corporate_event_backfill_plans(
        _load(args.before),
        _load(args.after),
    )
    output = {
        "schema_version": "corporate-event-backfill-plan-diff.v1",
        "offline": True,
        "read_only": True,
        "diff": diff.to_dict(),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if diff.equal else 1


if __name__ == "__main__":
    raise SystemExit(main())
