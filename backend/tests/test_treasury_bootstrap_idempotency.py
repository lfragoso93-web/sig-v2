from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import treasury_catalog_service, treasury_reconciliation_service


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _ScalarsResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        scalar_proxy = MagicMock()
        scalar_proxy.all.return_value = list(self._rows)
        return scalar_proxy


@pytest.mark.asyncio
async def test_treasury_catalog_second_execution_is_convergent(monkeypatch):
    item = {
        "symbol": "tesouro-selic-2029",
        "name": "Tesouro Selic",
        "maturityYear": 2029,
        "source": "tesouro_transparente_csv",
        "indexer": "SELIC",
    }
    monkeypatch.setattr(
        treasury_catalog_service,
        "fetch_treasury_catalog",
        AsyncMock(return_value=[item]),
    )
    monkeypatch.setattr(
        treasury_catalog_service,
        "consolidate_legacy_educa_identities",
        AsyncMock(return_value=SimpleNamespace(consolidated=0, errors=0)),
    )

    asset = SimpleNamespace(
        ticker="tesouro-selic-2029",
        asset_type="TESOURO_DIRETO",
        name="Tesouro Selic 2029",
        sector="Tesouro Direto | SELIC | fonte=tesouro_transparente_csv",
        currency="BRL",
    )
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _ScalarResult(None),
            _ScalarResult(asset),
        ]
    )

    first = await treasury_catalog_service.seed_treasury_assets(db)
    second = await treasury_catalog_service.seed_treasury_assets(db)

    assert first.created == 1
    assert first.updated == 0
    assert first.consolidated == 0
    assert first.errors == 0
    assert second.created == 0
    assert second.updated == 0
    assert second.skipped == 1
    assert second.consolidated == 0
    assert second.errors == 0
    assert db.add.call_count == 1
    assert db.flush.await_count == 2
    assert db.commit.await_count == 2


@pytest.mark.asyncio
async def test_treasury_reconciliation_second_execution_has_no_new_mutation(monkeypatch):
    transaction = SimpleNamespace(
        id=10,
        ticker="TESOURO SELIC 2029",
        asset_type="TESOURO_DIRETO",
    )
    db = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _ScalarsResult([transaction]),
            _ScalarsResult([transaction]),
        ]
    )

    monkeypatch.setattr(
        treasury_reconciliation_service,
        "resolve_treasury_symbol",
        AsyncMock(side_effect=["tesouro-selic-2029", "tesouro-selic-2029"]),
    )
    monkeypatch.setattr(
        treasury_reconciliation_service,
        "_ensure_asset",
        AsyncMock(side_effect=[True, False]),
    )

    first = await treasury_reconciliation_service.reconcile_treasury_transactions(db)
    second = await treasury_reconciliation_service.reconcile_treasury_transactions(db)

    assert first.scanned == 1
    assert first.updated_transactions == 1
    assert first.created_assets == 1
    assert first.errors == 0
    assert transaction.ticker == "tesouro-selic-2029"

    assert second.scanned == 1
    assert second.updated_transactions == 0
    assert second.created_assets == 0
    assert second.errors == 0
    assert db.commit.await_count == 2
