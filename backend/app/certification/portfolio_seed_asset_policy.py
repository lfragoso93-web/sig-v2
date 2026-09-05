"""Synthetic asset namespace policy for portfolio certification issue #303.

This module deliberately does not write to the database.  It converts the
human-readable fixture tickers into a reserved synthetic namespace before any
future seed step can create transactions or global market-source rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.certification.portfolio_seed_contract import (
    SYNTHETIC_OWNERSHIP_MARKER,
    SyntheticSeedContractError,
)
from app.certification.portfolio_synthetic_fixture import (
    load_portfolio_synthetic_certification_fixture,
)


SYNTHETIC_ASSET_PREFIX = "CERT303-"
SYNTHETIC_ASSET_PROVIDER = "synthetic-certification"
SYNTHETIC_ASSET_PROVIDER_STATUS = "synthetic-owned"


@dataclass(frozen=True)
class SyntheticAssetIdentity:
    source_ticker: str
    ticker: str
    asset_type: str
    name: str
    provider: str
    provider_symbol: str
    provider_status: str
    ownership_marker: str


def syntheticize_ticker(source_ticker: str) -> str:
    """Map one fixture ticker to the issue-scoped synthetic namespace."""
    normalized = str(source_ticker or "").strip().upper()
    if not normalized:
        raise SyntheticSeedContractError("synthetic asset source ticker is required")
    if normalized.startswith(SYNTHETIC_ASSET_PREFIX):
        raise SyntheticSeedContractError("fixture ticker is already in synthetic namespace")
    return f"{SYNTHETIC_ASSET_PREFIX}{normalized}"


def synthetic_asset_name(source_ticker: str) -> str:
    normalized = str(source_ticker or "").strip().upper()
    if not normalized:
        raise SyntheticSeedContractError("synthetic asset source ticker is required")
    return f"SGI certification #303 synthetic asset [{normalized}]"


def build_synthetic_asset_plan(fixture: dict[str, Any] | None = None) -> dict[str, SyntheticAssetIdentity]:
    """Build a deterministic, collision-resistant asset identity plan.

    The returned dictionary is keyed by the original fixture ticker.  Future
    transaction, price and dividend seed steps must use ``identity.ticker`` and
    must never persist global source data under the original real-world ticker.
    """
    payload = fixture or load_portfolio_synthetic_certification_fixture()
    transactions = payload.get("transactions")
    if not isinstance(transactions, list) or not transactions:
        raise SyntheticSeedContractError("synthetic fixture has no transactions")

    plan: dict[str, SyntheticAssetIdentity] = {}
    for row in transactions:
        source_ticker = str(row.get("ticker") or "").strip().upper()
        asset_type = str(row.get("asset_type") or "").strip().upper()
        if not source_ticker or not asset_type:
            raise SyntheticSeedContractError("synthetic asset identity is incomplete")

        current = SyntheticAssetIdentity(
            source_ticker=source_ticker,
            ticker=syntheticize_ticker(source_ticker),
            asset_type=asset_type,
            name=synthetic_asset_name(source_ticker),
            provider=SYNTHETIC_ASSET_PROVIDER,
            provider_symbol=source_ticker,
            provider_status=SYNTHETIC_ASSET_PROVIDER_STATUS,
            ownership_marker=SYNTHETIC_OWNERSHIP_MARKER,
        )
        previous = plan.get(source_ticker)
        if previous is not None and previous.asset_type != current.asset_type:
            raise SyntheticSeedContractError(
                f"fixture ticker {source_ticker} has conflicting asset types"
            )
        plan[source_ticker] = current

    _validate_fixture_references(payload, plan)
    return plan


def _validate_fixture_references(
    fixture: dict[str, Any],
    plan: dict[str, SyntheticAssetIdentity],
) -> None:
    """Fail closed when prices/income refer to assets absent from transactions."""
    prices = fixture.get("market_prices", {}).get("prices", {})
    if not isinstance(prices, dict):
        raise SyntheticSeedContractError("synthetic market prices contract is invalid")
    for ticker in prices:
        normalized = str(ticker).strip().upper()
        if normalized not in plan:
            raise SyntheticSeedContractError(
                f"market price ticker {normalized} has no synthetic asset owner"
            )

    income_events = fixture.get("income_events", [])
    if not isinstance(income_events, list):
        raise SyntheticSeedContractError("synthetic income events contract is invalid")
    for event in income_events:
        normalized = str(event.get("ticker") or "").strip().upper()
        if normalized not in plan:
            raise SyntheticSeedContractError(
                f"income ticker {normalized} has no synthetic asset owner"
            )


def assert_persisted_asset_identity(
    *,
    ticker: str,
    asset_type: str,
    name: str | None,
    provider: str | None,
    provider_symbol: str | None,
    provider_status: str | None,
    expected: SyntheticAssetIdentity,
) -> None:
    """Prove an existing global Asset belongs to this certification namespace."""
    actual = (
        ticker,
        asset_type,
        name,
        provider,
        provider_symbol,
        provider_status,
    )
    wanted = (
        expected.ticker,
        expected.asset_type,
        expected.name,
        expected.provider,
        expected.provider_symbol,
        expected.provider_status,
    )
    if actual != wanted:
        raise SyntheticSeedContractError(
            "synthetic asset namespace collision; existing global asset is not owned by issue #303"
        )
