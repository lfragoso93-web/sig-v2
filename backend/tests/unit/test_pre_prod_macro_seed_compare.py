from __future__ import annotations

import json

import pytest

from app.services.pre_prod_macro_seed_compare import (
    compare_macro_seed_evidence,
    compare_macro_seed_files,
    load_macro_seed_evidence,
)
from app.services.pre_prod_macro_seed_contract import MacroSeedContractError

COMMIT_SHA = "a" * 40


def _indicator(name: str, rows: int) -> dict:
    return {
        "indicator": name,
        "rows": rows,
        "first_date": "2024-01-01" if rows else None,
        "last_date": "2026-07-25" if rows else None,
        "duplicate_rows": 0,
    }


def _evidence(run_id: str, *, imported: dict[str, int] | None = None) -> dict:
    indicators = [
        _indicator("CDI", 100),
        _indicator("SELIC", 100),
        _indicator("IPCA", 30),
        _indicator("IGPM", 30),
    ]
    return {
        "schema_version": "pre-prod-macro-seed.v1",
        "run_id": run_id,
        "branch": "stable-15jun",
        "commit_sha": COMMIT_SHA,
        "started_at": "2026-07-25T23:00:00+00:00",
        "finished_at": "2026-07-25T23:00:01+00:00",
        "duration_seconds": 1.0,
        "ok": True,
        "before": {
            "total_rows": 260,
            "indicators": indicators,
            "unsupported_indicators": [],
        },
        "after": {
            "total_rows": 260,
            "indicators": indicators,
            "unsupported_indicators": [],
        },
        "imported": imported or {"CDI": 0, "SELIC": 0, "IPCA": 0, "IGPM": 0},
        "errors": [],
    }


def test_compare_accepts_idempotent_second_execution():
    comparison = compare_macro_seed_evidence(
        _evidence("20260725-230632"),
        _evidence("20260725-231000"),
    )

    assert comparison.ok is True
    assert comparison.stable_after_state is True
    assert comparison.zero_new_rows_on_second_run is True
    assert comparison.differences == ()
    assert comparison.to_dict()["schema_version"] == "pre-prod-macro-seed-compare.v1"


def test_compare_rejects_new_rows_on_second_execution():
    comparison = compare_macro_seed_evidence(
        _evidence("20260725-230632"),
        _evidence("20260725-231000", imported={"CDI": 1}),
    )

    assert comparison.ok is False
    assert comparison.zero_new_rows_on_second_run is False
    assert "segunda execução importou novas linhas" in comparison.differences


def test_compare_detects_state_change():
    first = _evidence("20260725-230632")
    second = _evidence("20260725-231000")
    second["after"]["total_rows"] = 261
    second["after"]["indicators"][0]["rows"] = 101

    comparison = compare_macro_seed_evidence(first, second)

    assert comparison.ok is False
    assert comparison.stable_after_state is False
    assert "estado final difere entre as execuções" in comparison.differences


def test_compare_detects_different_commit():
    second = _evidence("20260725-231000")
    second["commit_sha"] = "b" * 40

    comparison = compare_macro_seed_evidence(
        _evidence("20260725-230632"),
        second,
    )

    assert comparison.ok is False
    assert comparison.same_commit is False


def test_load_rejects_failed_evidence(tmp_path):
    path = tmp_path / "failed.json"
    payload = _evidence("20260725-230632")
    payload["ok"] = False
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(MacroSeedContractError, match="bem-sucedidas"):
        load_macro_seed_evidence(path)


def test_compare_files_loads_utf8_json(tmp_path):
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    first_path.write_text(
        json.dumps(_evidence("20260725-230632"), ensure_ascii=False),
        encoding="utf-8",
    )
    second_path.write_text(
        json.dumps(_evidence("20260725-231000"), ensure_ascii=False),
        encoding="utf-8",
    )

    assert compare_macro_seed_files(first_path, second_path).ok is True
