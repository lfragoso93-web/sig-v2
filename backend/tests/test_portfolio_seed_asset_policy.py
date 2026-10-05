from copy import deepcopy

import pytest

from app.certification import portfolio_seed_asset_policy as policy
from app.certification.portfolio_seed_contract import SyntheticSeedContractError
from app.certification.portfolio_synthetic_fixture import (
    load_portfolio_synthetic_certification_fixture,
)


def test_asset_plan_maps_fixture_tickers_to_reserved_namespace() -> None:
    plan = policy.build_synthetic_asset_plan()

    assert plan["PETR4"].ticker == "CERT303-PETR4"
    assert plan["MXRF11"].ticker == "CERT303-MXRF11"
    assert plan["BOVA11"].ticker == "CERT303-BOVA11"
    assert plan["AAPL34"].ticker == "CERT303-AAPL34"
    assert plan["BTC"].ticker == "CERT303-BTC"
    assert plan["TESOURO-SELIC-2029"].ticker == "CERT303-TESOURO-SELIC-2029"
    assert plan["CDB-SYN-CDI-2028"].ticker == "CERT303-CDB-SYN-CDI-2028"
    assert {identity.ticker for identity in plan.values()} == {
        "CERT303-PETR4",
        "CERT303-MXRF11",
        "CERT303-BOVA11",
        "CERT303-AAPL34",
        "CERT303-BTC",
        "CERT303-TESOURO-SELIC-2029",
        "CERT303-CDB-SYN-CDI-2028",
    }
    assert all(identity.ticker.startswith("CERT303-") for identity in plan.values())
    assert all(identity.provider == "synthetic-certification" for identity in plan.values())
    assert all(identity.provider_status == "synthetic-owned" for identity in plan.values())
    assert all(identity.ownership_marker == "sgi:certification:issue-303:v1" for identity in plan.values())


def test_asset_plan_preserves_asset_types_and_source_symbols() -> None:
    fixture = load_portfolio_synthetic_certification_fixture()
    plan = policy.build_synthetic_asset_plan(fixture)

    expected_types = {}
    for row in fixture["transactions"]:
        expected_types[row["ticker"]] = row["asset_type"]

    assert {ticker: identity.asset_type for ticker, identity in plan.items()} == expected_types
    assert all(identity.provider_symbol == ticker for ticker, identity in plan.items())


def test_asset_plan_rejects_conflicting_asset_type_for_same_fixture_ticker() -> None:
    fixture = deepcopy(load_portfolio_synthetic_certification_fixture())
    fixture["transactions"].append(
        {
            **fixture["transactions"][0],
            "asset_type": "FII",
        }
    )

    with pytest.raises(SyntheticSeedContractError, match="conflicting asset types"):
        policy.build_synthetic_asset_plan(fixture)


def test_asset_plan_rejects_price_without_transaction_owner() -> None:
    fixture = deepcopy(load_portfolio_synthetic_certification_fixture())
    fixture["market_prices"]["prices"]["ORPHAN"] = "1.00"

    with pytest.raises(SyntheticSeedContractError, match="market price ticker ORPHAN"):
        policy.build_synthetic_asset_plan(fixture)


def test_asset_plan_rejects_income_without_transaction_owner() -> None:
    fixture = deepcopy(load_portfolio_synthetic_certification_fixture())
    fixture["income_events"].append(
        {
            **fixture["income_events"][0],
            "ticker": "ORPHAN",
        }
    )

    with pytest.raises(SyntheticSeedContractError, match="income ticker ORPHAN"):
        policy.build_synthetic_asset_plan(fixture)


def test_syntheticize_ticker_rejects_empty_or_already_namespaced_input() -> None:
    for ticker in ("", "   ", None):
        with pytest.raises(SyntheticSeedContractError, match="source ticker is required"):
            policy.syntheticize_ticker(ticker)  # type: ignore[arg-type]

    with pytest.raises(SyntheticSeedContractError, match="already in synthetic namespace"):
        policy.syntheticize_ticker("CERT303-PETR4")


def test_persisted_asset_identity_accepts_only_exact_owned_metadata() -> None:
    expected = policy.build_synthetic_asset_plan()["PETR4"]

    policy.assert_persisted_asset_identity(
        ticker=expected.ticker,
        asset_type=expected.asset_type,
        name=expected.name,
        provider=expected.provider,
        provider_symbol=expected.provider_symbol,
        provider_status=expected.provider_status,
        expected=expected,
    )

    with pytest.raises(SyntheticSeedContractError, match="namespace collision"):
        policy.assert_persisted_asset_identity(
            ticker=expected.ticker,
            asset_type=expected.asset_type,
            name="real asset accidentally using reserved ticker",
            provider=expected.provider,
            provider_symbol=expected.provider_symbol,
            provider_status=expected.provider_status,
            expected=expected,
        )
