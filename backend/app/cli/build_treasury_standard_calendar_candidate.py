"""Build a complete Treasury-standard calendar candidate without persistence.

The command reads only its reviewed local input file.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.services.market_calendar_promotion_plan import (
    build_treasury_standard_calendar_candidate,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ordinary_rule_file", type=Path)
    args = parser.parse_args()

    with args.ordinary_rule_file.open(encoding="utf-8") as handle:
        ordinary_rule = json.load(handle)
    if not isinstance(ordinary_rule, dict):
        raise ValueError("market calendar ordinary rule must be an object")

    candidate = build_treasury_standard_calendar_candidate(ordinary_rule)
    print(json.dumps(candidate, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
