"""Emit a fail-closed, non-persistent market-calendar promotion plan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.services.market_calendar_promotion_plan import (
    build_market_calendar_promotion_plan,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate_file", type=Path)
    args = parser.parse_args()

    with args.candidate_file.open(encoding="utf-8") as handle:
        candidate = json.load(handle)
    if not isinstance(candidate, dict):
        raise ValueError("market calendar candidate must be an object")

    plan = build_market_calendar_promotion_plan(candidate)
    print(
        json.dumps(
            plan.to_dict(), ensure_ascii=False, indent=2, sort_keys=True
        )
    )
    return 0 if plan.promotable else 2


if __name__ == "__main__":
    raise SystemExit(main())
