from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.cli import pre_prod_treasury_seed_idempotency as cli
from app.services.pre_prod_treasury_seed_contract import (
    PreProdTreasurySeedResult,
    TreasurySeedCounts,
    TreasurySeedCoverage,
)

COUNTS = TreasurySeedCounts(assets=24, aliases=10, prices=1488)
COVERAGE = TreasurySeedCoverage(
    first_price_date="2023-08-01",
    last_price_date="2026-07-25",
    priced_assets=24,
)


def _payload(run_id: str) -> dict:
    return PreProdTreasurySeedResult(
        run_id=run_id,
        branch="stable-15jun",
        commit_sha="a" * 40,
        started_at="2026-07-25T20:00:00+00:00",
        finished_at="2026-07-25T20:01:00+00:00",
        duration_seconds=60.0,
        ok=True,
        before=COUNTS,
        after=COUNTS,
        coverage=COVERAGE,
    ).to_dict()


def _write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_cli_returns_zero_for_idempotent_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    _write(first, _payload("20260725-200000"))
    _write(second, _payload("20260725-200200"))
    monkeypatch.setattr(
        cli,
        "_parser",
        lambda: type(
            "Parser",
            (),
            {"parse_args": lambda self: type("Args", (), {"first": first, "second": second})()},
        )(),
    )

    assert cli.main() == cli.EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["same_state"] is True
    assert payload["same_coverage"] is True
    assert payload["chained_baseline"] is True


def test_cli_returns_one_for_non_idempotent_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    _write(first, _payload("20260725-200000"))
    changed = _payload("20260725-200200")
    changed["after"]["prices"] = 1489
    changed["before"]["prices"] = 1489
    _write(second, changed)
    monkeypatch.setattr(
        cli,
        "_parser",
        lambda: type(
            "Parser",
            (),
            {"parse_args": lambda self: type("Args", (), {"first": first, "second": second})()},
        )(),
    )

    assert cli.main() == cli.EXIT_NOT_IDEMPOTENT
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["same_state"] is False


def test_cli_returns_two_for_invalid_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text("not-json", encoding="utf-8")
    _write(second, _payload("20260725-200200"))
    monkeypatch.setattr(
        cli,
        "_parser",
        lambda: type(
            "Parser",
            (),
            {"parse_args": lambda self: type("Args", (), {"first": first, "second": second})()},
        )(),
    )

    assert cli.main() == cli.EXIT_INVALID_INPUT
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "ok": False,
        "error": "evidência inválida",
        "type": "JSONDecodeError",
    }
