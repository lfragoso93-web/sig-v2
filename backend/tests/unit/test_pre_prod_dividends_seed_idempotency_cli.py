from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.cli import pre_prod_dividends_seed_idempotency as cli
from app.services.pre_prod_dividends_seed_contract import (
    DividendsSeedCounts,
    DividendsSeedCoverage,
    DividendsSeedIntegrity,
    DividendsSeedTransaction,
    DividendsSeedWindow,
    PreProdDividendsSeedResult,
)


def _payload(run_id: str, *, created: int = 0) -> dict:
    counts = DividendsSeedCounts(10, 30, 1)
    return PreProdDividendsSeedResult(
        run_id=run_id,
        branch="stable-15jun",
        commit_sha="a" * 40,
        generated_at="2026-07-28T21:00:00+00:00",
        ok=True,
        window=DividendsSeedWindow("2020-01-01", "2026-07-28"),
        before=counts,
        after=counts,
        coverage=DividendsSeedCoverage(),
        integrity=DividendsSeedIntegrity(),
        transaction=DividendsSeedTransaction("committed", True, False),
        groupings=(),
        sources=(),
        collection={"assets": 0, "normalized_rows": 0},
        global_persistence={"created": created, "updated": 0, "unchanged": 0},
    ).to_dict()


def _write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _args(monkeypatch: pytest.MonkeyPatch, first: Path, second: Path) -> None:
    monkeypatch.setattr(
        cli,
        "_parser",
        lambda: type(
            "Parser",
            (),
            {
                "parse_args": lambda self: type(
                    "Args", (), {"first": first, "second": second}
                )()
            },
        )(),
    )


def test_cli_returns_zero_for_idempotent_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    _write(first, _payload("20260728-180000", created=2))
    _write(second, _payload("20260728-180200"))
    _args(monkeypatch, first, second)

    assert cli.main() == cli.EXIT_OK
    assert json.loads(capsys.readouterr().out)["ok"] is True


def test_cli_returns_one_for_non_idempotent_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    _write(first, _payload("20260728-180000", created=2))
    _write(second, _payload("20260728-180200", created=1))
    _args(monkeypatch, first, second)

    assert cli.main() == cli.EXIT_NOT_IDEMPOTENT
    assert json.loads(capsys.readouterr().out)["ok"] is False


def test_cli_returns_two_for_invalid_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text("not-json", encoding="utf-8")
    _write(second, _payload("20260728-180200"))
    _args(monkeypatch, first, second)

    assert cli.main() == cli.EXIT_INVALID_INPUT
    assert json.loads(capsys.readouterr().out)["error"] == "evidência inválida"
