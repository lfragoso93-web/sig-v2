from __future__ import annotations

import sys
from copy import deepcopy
from decimal import Decimal

import pytest

from app.cli import cleanup_treasury_legacy_assets as cli
from app.services import treasury_legacy_cleanup as service


def valid_snapshot() -> dict:
    return {
        "assets": {
            "4742": {"id": 4742, "ticker": "tesouro-educa-15122030", "asset_type": "TESOURO_DIRETO"},
            "4747": {"id": 4747, "ticker": "tesouro-educa-15122031", "asset_type": "TESOURO_DIRETO"},
            "4810": {"id": 4810, "ticker": "tesouro-educa-mais-2030", "asset_type": "TESOURO_DIRETO"},
            "4823": {"id": 4823, "ticker": "tesouro-educa-mais-2031", "asset_type": "TESOURO_DIRETO"},
        },
        "aliases": {
            "tesouro-educa-15122030": [],
            "tesouro-educa-15122031": [],
        },
        "functional_references": {
            "asset_dividends.asset_id": 0,
            "corporate_events.asset_id": 0,
            "portfolio_positions.asset_id": 0,
            "transactions.asset_id": 0,
        },
        "legacy_prices": {
            "4742": {
                "count": 2,
                "enriched": 0,
                "min_close": Decimal("3518.20"),
                "max_close": Decimal("3522.89"),
                "min_timestamp": "2026-07-24T12:00:00+00:00",
                "max_timestamp": "2026-07-25T12:00:00+00:00",
            },
            "4747": {
                "count": 2,
                "enriched": 0,
                "min_close": Decimal("3769.72"),
                "max_close": Decimal("3777.79"),
                "min_timestamp": "2026-07-24T12:00:00+00:00",
                "max_timestamp": "2026-07-25T12:00:00+00:00",
            },
        },
        "official_prices": {
            "4810": {"count": 743, "enriched": 743, "min_close": Decimal("1"), "max_close": Decimal("2"), "min_timestamp": "a", "max_timestamp": "b"},
            "4823": {"count": 743, "enriched": 743, "min_close": Decimal("1"), "max_close": Decimal("2"), "min_timestamp": "a", "max_timestamp": "b"},
        },
        "integrity": {"orphan_prices": 0, "duplicate_prices": 0},
    }


def applied_snapshot(before: dict) -> dict:
    after = deepcopy(before)
    after["assets"]["4742"] = None
    after["assets"]["4747"] = None
    after["aliases"]["tesouro-educa-15122030"] = [{"id": 1, "asset_id": 4810, "alias_ticker": "tesouro-educa-15122030", "asset_type": "TESOURO_DIRETO", "source_provider": service.SCHEMA_VERSION}]
    after["aliases"]["tesouro-educa-15122031"] = [{"id": 2, "asset_id": 4823, "alias_ticker": "tesouro-educa-15122031", "asset_type": "TESOURO_DIRETO", "source_provider": service.SCHEMA_VERSION}]
    after["legacy_prices"]["4742"]["count"] = 0
    after["legacy_prices"]["4747"]["count"] = 0
    return after


class Result:
    def __init__(self, rowcount: int = 1):
        self.rowcount = rowcount


class Connection:
    def __init__(self):
        self.calls = []

    def execute(self, statement, params=None):
        self.calls.append((str(statement), params))
        sql = str(statement)
        if sql.startswith("DELETE FROM asset_prices"):
            return Result(4)
        if sql.startswith("DELETE FROM assets"):
            return Result(2)
        return Result(1)


def test_dry_run_does_not_write(monkeypatch):
    connection = Connection()
    monkeypatch.setattr(service, "inspect", lambda _: valid_snapshot())
    report = service.execute(connection)
    assert report["status"] == "validated"
    assert connection.calls == []


def test_apply_and_second_execution_are_safe(monkeypatch):
    before = valid_snapshot()
    after = applied_snapshot(before)
    snapshots = iter((before, after))
    monkeypatch.setattr(service, "inspect", lambda _: next(snapshots))
    report = service.execute(Connection(), apply=True)
    assert report["status"] == "applied"
    monkeypatch.setattr(service, "inspect", lambda _: after)
    assert service.execute(Connection(), apply=True)["status"] == "already-applied"


@pytest.mark.parametrize("mutation", ("alias", "reference", "asset", "price_count", "price_value", "official"))
def test_divergence_is_rejected(monkeypatch, mutation):
    snapshot = valid_snapshot()
    if mutation == "alias":
        snapshot["aliases"]["tesouro-educa-15122030"] = [{"asset_id": 999}]
    elif mutation == "reference":
        snapshot["functional_references"]["transactions.asset_id"] = 1
    elif mutation == "asset":
        snapshot["assets"]["4742"]["ticker"] = "outro"
    elif mutation == "price_count":
        snapshot["legacy_prices"]["4742"]["count"] = 1
    elif mutation == "price_value":
        snapshot["legacy_prices"]["4742"]["max_close"] = Decimal("3522.90")
    else:
        snapshot["official_prices"]["4810"]["count"] = 742
    monkeypatch.setattr(service, "inspect", lambda _: snapshot)
    with pytest.raises(service.TreasuryLegacyCleanupError):
        service.execute(Connection(), apply=True)


def test_failure_before_post_validation_aborts(monkeypatch):
    monkeypatch.setattr(service, "inspect", lambda _: valid_snapshot())
    with pytest.raises(RuntimeError, match="forced"):
        service.execute(Connection(), apply=True, before_post_validation=lambda: (_ for _ in ()).throw(RuntimeError("forced")))


def test_help_and_unknown_arguments_do_not_create_engine(monkeypatch, capsys):
    monkeypatch.setattr(cli, "create_engine", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("database access")))
    monkeypatch.setattr(sys, "argv", ["cleanup", "--help"])
    with pytest.raises(SystemExit) as help_exit:
        cli.main()
    assert help_exit.value.code == 0
    assert "usage:" in capsys.readouterr().out
    with pytest.raises(SystemExit) as unknown_exit:
        cli.run(["--unknown"])
    assert unknown_exit.value.code == 2
