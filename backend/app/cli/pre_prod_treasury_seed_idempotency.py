from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.services.pre_prod_treasury_seed_contract import (
    PreProdTreasurySeedResult,
    TreasurySeedCounts,
    TreasurySeedCoverage,
)
from app.services.pre_prod_treasury_seed_idempotency import (
    compare_treasury_seed_runs,
)

EXIT_OK = 0
EXIT_NOT_IDEMPOTENT = 1
EXIT_INVALID_INPUT = 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compara duas evidências JSON consecutivas do seed isolado do "
            "Tesouro Direto"
        )
    )
    parser.add_argument("--first", required=True, type=Path)
    parser.add_argument("--second", required=True, type=Path)
    return parser


def _counts(payload: dict[str, Any]) -> TreasurySeedCounts:
    return TreasurySeedCounts(**payload)


def _coverage(payload: dict[str, Any]) -> TreasurySeedCoverage:
    return TreasurySeedCoverage(**payload)


def _result(payload: dict[str, Any]) -> PreProdTreasurySeedResult:
    return PreProdTreasurySeedResult(
        run_id=str(payload["run_id"]),
        branch=str(payload["branch"]),
        commit_sha=str(payload["commit_sha"]),
        started_at=str(payload["started_at"]),
        finished_at=str(payload["finished_at"]),
        duration_seconds=float(payload["duration_seconds"]),
        ok=bool(payload["ok"]),
        before=_counts(dict(payload["before"])),
        after=_counts(dict(payload["after"])),
        coverage=_coverage(dict(payload["coverage"])),
        catalog=dict(payload.get("catalog") or {}),
        history=dict(payload.get("history") or {}),
        errors=tuple(str(item) for item in payload.get("errors") or ()),
        schema_version=str(payload["schema_version"]),
    )


def _read(path: Path) -> PreProdTreasurySeedResult:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("evidência deve conter um objeto JSON")
    return _result(payload)


def main() -> int:
    args = _parser().parse_args()
    try:
        first = _read(args.first)
        second = _read(args.second)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {"ok": False, "error": "evidência inválida", "type": type(exc).__name__},
                ensure_ascii=False,
            )
        )
        return EXIT_INVALID_INPUT

    result = compare_treasury_seed_runs(first, second)
    print(json.dumps(result.to_dict(), ensure_ascii=False))
    return EXIT_OK if result.ok else EXIT_NOT_IDEMPOTENT


if __name__ == "__main__":
    raise SystemExit(main())
