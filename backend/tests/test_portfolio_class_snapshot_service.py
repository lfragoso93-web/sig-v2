from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.models.asset import AssetType
from app.models.asset import Asset
from app.models.asset_price import AssetPrice
from app.services.canonical_dividend_entitlement import (
    DividendEntitlement,
    DividendEvent,
    EntitlementReason,
)
from app.services.canonical_dividend_entitlement_reader import (
    PortfolioDividendEntitlement,
)
from app.services.portfolio_class_reconciliation_service import _check
from app.services.portfolio_class_snapshot_read_service import class_snapshot_payload
from app.services.portfolio_class_snapshot_service import (
    _group_received_dividends,
    _load_exact_treasury_prices,
    _next_business_date,
    class_twr_availability,
)


def test_availability_refuses_dedicated_history_estimates() -> None:
    rows = class_twr_availability(
        [AssetType.ACAO, AssetType.FII, AssetType.TESOURO_DIRETO, AssetType.RENDA_FIXA]
    )
    by_type = {row["asset_type"]: row for row in rows}

    assert by_type[AssetType.ACAO.value]["available"] is True
    assert by_type[AssetType.FII.value]["status"] == "available"
    assert by_type[AssetType.TESOURO_DIRETO.value]["available"] is True
    assert by_type[AssetType.RENDA_FIXA.value]["status"] == "dedicated_history_not_available"


async def test_treasury_exact_prices_do_not_use_prior_day_fallback(db) -> None:
    asset = Asset(
        ticker="TESOURO-SELIC-01032031",
        name="Tesouro Selic 2031",
        asset_type=AssetType.TESOURO_DIRETO.value,
        currency="BRL",
    )
    db.add(asset)
    await db.flush()
    db.add_all(
        [
            AssetPrice(
                asset_id=asset.id,
                timestamp=datetime(2026, 8, 3, 18, tzinfo=UTC),
                close=Decimal("100.00"),
                source="tesouro_transparente",
            ),
            AssetPrice(
                asset_id=asset.id,
                timestamp=datetime(2026, 8, 4, 18, tzinfo=UTC),
                close=Decimal("101.00"),
                source="tesouro_transparente",
            ),
        ]
    )
    await db.flush()

    prices = await _load_exact_treasury_prices(
        db,
        ["tesouro-selic-01032031"],
        date(2026, 8, 4),
    )
    missing = await _load_exact_treasury_prices(
        db,
        ["tesouro-selic-01032031"],
        date(2026, 8, 5),
    )

    assert prices == {"TESOURO-SELIC-01032031": Decimal("101.00000000")}
    assert missing == {}


def test_non_business_dates_move_to_next_close() -> None:
    assert _next_business_date(date(2026, 7, 17)) == date(2026, 7, 17)
    assert _next_business_date(date(2026, 7, 18)) == date(2026, 7, 20)
    assert _next_business_date(date(2026, 7, 19)) == date(2026, 7, 20)


def test_received_dividends_are_grouped_by_class_and_effective_close() -> None:
    entitlements = [
        _entitlement("ABCD3", "ACAO", date(2026, 7, 18), "12.34"),
        _entitlement("FUND11", "FII", date(2026, 7, 20), "5.00"),
        _entitlement(
            "ABCD3",
            "ACAO",
            date(2026, 7, 20),
            "99.00",
            reason=EntitlementReason.NO_POSITION,
        ),
    ]

    grouped = _group_received_dividends(entitlements)

    assert grouped[(AssetType.ACAO, date(2026, 7, 20))] == Decimal("12.34")
    assert grouped[(AssetType.FII, date(2026, 7, 20))] == Decimal("5.00")


def _entitlement(
    ticker: str,
    asset_type: str,
    payment_date: date,
    amount: str,
    *,
    reason: EntitlementReason = EntitlementReason.ELIGIBLE,
) -> PortfolioDividendEntitlement:
    event = DividendEvent(
        event_id=1,
        record_date=date(2026, 7, 1),
        ex_date=date(2026, 7, 2),
        payment_date=payment_date,
        event_type="DIVIDENDO",
        value_per_unit=Decimal("1"),
        currency="BRL",
    )
    right = DividendEntitlement(
        event_id=1,
        reason=reason,
        entitlement_date=event.record_date,
        eligible_quantity=Decimal("1"),
        gross_amount=Decimal(amount),
        withholding_tax=Decimal("0"),
        net_amount=Decimal(amount),
        currency="BRL",
    )
    return PortfolioDividendEntitlement(
        ticker=ticker,
        asset_type=asset_type,
        event=event,
        entitlement=right,
        approved_on=None,
        gross_value_per_unit=None,
        factor=None,
        complete_factor=None,
        isin_code=None,
        asset_issued=None,
        related_to=None,
        remarks=None,
    )


def test_class_snapshot_payload_exposes_quality_and_twr() -> None:
    snapshot = SimpleNamespace(
        asset_type="ACAO",
        snapshot_date=date(2026, 7, 15),
        market_value=Decimal("1200.00"),
        cost_basis=Decimal("1000.00"),
        realized_pnl=Decimal("50.00"),
        unrealized_pnl=Decimal("200.00"),
        net_external_flow=Decimal("0.00"),
        dividends_day=Decimal("10.00"),
        dividends_accumulated=Decimal("80.00"),
        daily_return_pct=Decimal("1.234567"),
        accumulated_return_pct=Decimal("8.765432"),
        has_partial_prices=False,
        return_is_estimated=True,
        valuation_status="complete",
    )

    payload = class_snapshot_payload(snapshot)

    assert payload["history_source"] == "portfolio_class_snapshot"
    assert payload["daily_return_pct"] == 1.234567
    assert payload["accumulated_return_pct"] == 8.765432
    assert payload["return_is_estimated"] is True
    assert payload["valuation_status"] == "complete"


def test_reconciliation_check_preserves_sign_and_tolerance() -> None:
    reconciled = _check("market_value", Decimal("100.00"), Decimal("100.01"))
    failed = _check("market_value", Decimal("100.00"), Decimal("99.98"))

    assert reconciled["is_reconciled"] is True
    assert reconciled["difference"] == 0.01
    assert failed["is_reconciled"] is False
    assert failed["difference"] == -0.02
