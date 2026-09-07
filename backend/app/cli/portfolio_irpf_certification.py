"""CLI read-only para certificar o IRPF canônico da carteira sintética #303."""

from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal

from app.certification.portfolio_certification_identity import (
    load_certification_portfolio_identity,
)
from app.certification.portfolio_irpf_expectations import (
    EXPECTED_DISPOSALS_2026,
    EXPECTED_SYNTHETIC_IRPF_2026,
)
from app.core.database import AsyncSessionLocal
from app.services.irpf_annual_integrated_assessment_service import (
    assess_annual_integrated_operations,
)
from app.services.irpf_realized_disposal_tax_adapter import adapt_realized_disposals
from app.services.realized_pnl_projection_reader import load_realized_disposals

_CENT = Decimal("0.01")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(_CENT)


async def main() -> None:
    expected = EXPECTED_SYNTHETIC_IRPF_2026
    failures: list[str] = []

    async with AsyncSessionLocal() as db:
        portfolio_id, _ = await load_certification_portfolio_identity(db)
        disposals = await load_realized_disposals(
            db,
            portfolio_id,
            start_date=date(expected.year, 1, 1),
            end_date=date(expected.year, 12, 31),
        )
        fiscal_entries = adapt_realized_disposals(disposals)
        assessment = await assess_annual_integrated_operations(
            db,
            portfolio_id,
            expected.year,
        )
        await db.rollback()

    if len(fiscal_entries) != expected.disposal_count:
        failures.append(
            f"disposal-count:actual={len(fiscal_entries)}:expected={expected.disposal_count}"
        )

    entries_by_ticker = {entry.ticker: entry for entry in fiscal_entries}
    if set(entries_by_ticker) != set(EXPECTED_DISPOSALS_2026):
        failures.append(
            "disposal-tickers:actual="
            + ",".join(sorted(entries_by_ticker))
            + ":expected="
            + ",".join(sorted(EXPECTED_DISPOSALS_2026))
        )

    monthly_by_group = {item.group.value: item for item in assessment.swing.monthly}
    for ticker, wanted in EXPECTED_DISPOSALS_2026.items():
        entry = entries_by_ticker.get(ticker)
        if entry is None:
            continue
        for field in (
            "gross_proceeds_brl",
            "cost_basis_brl",
            "fees_brl",
            "realized_pnl_brl",
        ):
            actual = _money(getattr(entry, field))
            target = wanted[field]
            if actual != target:
                failures.append(
                    f"{ticker}:{field}:actual={actual}:expected={target}"
                )
        if entry.common_group.value != wanted["fiscal_group"]:
            failures.append(
                f"{ticker}:fiscal-group:actual={entry.common_group.value}:"
                f"expected={wanted['fiscal_group']}"
            )
        monthly = monthly_by_group.get(wanted["fiscal_group"])
        if monthly is None:
            failures.append(f"{ticker}:missing-monthly-assessment")
        elif monthly.exemption_applied is not wanted["exemption_applied"]:
            failures.append(
                f"{ticker}:exemption:actual={monthly.exemption_applied}:"
                f"expected={wanted['exemption_applied']}"
            )

    gross_sales = sum(
        (_money(entry.gross_proceeds_brl) for entry in fiscal_entries),
        start=Decimal("0.00"),
    )
    common_withholding = sum(
        (_money(item.current_withholding_brl) for item in assessment.common_withholding_monthly),
        start=Decimal("0.00"),
    )
    comparisons = {
        "gross-sales": (gross_sales, expected.total_common_gross_sales_brl),
        "swing-realized": (
            _money(assessment.total_swing_realized_pnl_brl),
            expected.total_swing_realized_pnl_brl,
        ),
        "swing-taxable-base": (
            _money(assessment.total_swing_taxable_base_brl),
            expected.total_swing_taxable_base_brl,
        ),
        "swing-tax-due": (
            _money(assessment.total_swing_tax_due_brl),
            expected.total_swing_tax_due_brl,
        ),
        "common-withholding": (common_withholding, expected.common_withholding_brl),
        "swing-net-tax-due": (
            _money(assessment.total_swing_net_tax_due_brl),
            expected.total_swing_net_tax_due_brl,
        ),
        "payment-due": (
            _money(assessment.total_payment_due_brl),
            expected.total_payment_due_brl,
        ),
        "day-trade-result": (
            _money(assessment.total_day_trade_result_brl),
            expected.total_day_trade_result_brl,
        ),
        "day-trade-tax": (
            _money(assessment.total_day_trade_tax_due_brl),
            expected.total_day_trade_tax_due_brl,
        ),
    }
    for label, (actual, wanted) in comparisons.items():
        if actual != wanted:
            failures.append(f"{label}:actual={actual}:expected={wanted}")

    print(
        "CERT303-IRPF",
        f"portfolio_id={portfolio_id}",
        f"year={expected.year}",
        f"disposals={len(fiscal_entries)}",
        f"gross_sales={gross_sales}",
        f"swing_realized={_money(assessment.total_swing_realized_pnl_brl)}",
        f"taxable_base={_money(assessment.total_swing_taxable_base_brl)}",
        f"gross_tax={_money(assessment.total_swing_tax_due_brl)}",
        f"irrf={common_withholding}",
        f"net_tax={_money(assessment.total_swing_net_tax_due_brl)}",
        f"payment_due={_money(assessment.total_payment_due_brl)}",
        f"day_trade_tax={_money(assessment.total_day_trade_tax_due_brl)}",
        f"status={'PASS' if not failures else 'FAIL'}",
    )
    if failures:
        raise RuntimeError("; ".join(failures))


if __name__ == "__main__":
    asyncio.run(main())
