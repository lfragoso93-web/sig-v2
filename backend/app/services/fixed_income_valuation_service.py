"""
fixed_income_valuation_service.py

Valuation de Renda Fixa sem conceito de cotas.

Regra de negócio:
- Cada compra de RENDA_FIXA é tratada como uma aplicação individual.
- O valor aplicado é quantity * price + fees.
- Cada aplicação rende a partir da sua própria data.
- O agrupamento final ocorre somente quando forem iguais:
    1. nome/ticker
    2. indexador
    3. percentual/taxa informado
    4. vencimento
- O valor aplicado e a data de aplicação NÃO entram na chave de agrupamento.

A correção usa a série histórica persistida em rate_history, importada do SGS/BCB.
Quando não há histórico suficiente, cai para um fallback anual conservador.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction, OperationType
from app.services.benchmark_rate_service import benchmark_factor, latest_annual_reference_pct

logger = logging.getLogger(__name__)

RENDA_FIXA_TYPE = "RENDA_FIXA"

_DEFAULT_CDI_ANNUAL_PCT = Decimal("10.65")
_DEFAULT_SELIC_ANNUAL_PCT = Decimal("10.65")
_DEFAULT_IPCA_ANNUAL_PCT = Decimal("4.50")
_DEFAULT_IGPM_ANNUAL_PCT = Decimal("4.00")


@dataclass(frozen=True)
class FixedIncomeKey:
    name: str
    indexer: str
    rate_pct: Decimal
    maturity: Optional[date]


@dataclass
class FixedIncomeApplication:
    key: FixedIncomeKey
    invested_amount: Decimal
    date_start: date
    remaining_principal: Decimal


@dataclass
class FixedIncomeValuation:
    key: FixedIncomeKey
    invested_amount: Decimal
    current_value: Decimal
    income_amount: Decimal
    income_pct: Decimal
    applications_count: int


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _pct(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _decimal_from_str(value: object, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    try:
        return Decimal(str(value).replace(",", "."))
    except Exception:
        return Decimal(default)


def _operation_value(op: object) -> str:
    if isinstance(op, OperationType):
        return op.value
    return str(op or "").lower()


def _is_buy(op: object) -> bool:
    return _operation_value(op) in {"buy", "compra"}


def _is_sell(op: object) -> bool:
    return _operation_value(op) in {"sell", "venda", "resgate"}


def _normalize_indexer(raw: Optional[str]) -> str:
    if not raw:
        return "CDI"
    value = raw.strip().upper().replace("Í", "I")
    if value in {"IPCA+", "IPCA PLUS", "IPCA_PLUS", "IPCA"}:
        return "IPCA_PLUS"
    if value in {"IGP-M", "IGPM", "IGPM+", "IGP-M+", "IGPM_PLUS"}:
        return "IGPM_PLUS"
    if value in {"PREFIXADO", "PREFIXADA", "PRE", "PRÉ"}:
        return "PREFIXADO"
    if value == "SELIC":
        return "SELIC"
    if value == "CDI":
        return "CDI"
    return value


def _parse_notes(notes: Optional[str]) -> tuple[str, Decimal, Optional[date]]:
    text = notes or ""
    indexer: Optional[str] = None
    rate = Decimal("0")
    maturity: Optional[date] = None

    m = re.search(r"Indexador:\s*([^|\-\n]+)", text, re.IGNORECASE)
    if m:
        indexer = m.group(1).strip()

    m = re.search(r"([0-9]+(?:[\.,][0-9]+)?)\s*%\s*do\s+", text, re.IGNORECASE)
    if m:
        rate = _decimal_from_str(m.group(1))

    if rate == 0:
        m = re.search(r"Taxa:\s*([0-9]+(?:[\.,][0-9]+)?)\s*%", text, re.IGNORECASE)
        if m:
            rate = _decimal_from_str(m.group(1))

    m = re.search(r"Vencimento:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", text, re.IGNORECASE)
    if m:
        try:
            maturity = date.fromisoformat(m.group(1))
        except ValueError:
            maturity = None

    return _normalize_indexer(indexer), rate, maturity


async def _latest_refs(db: AsyncSession) -> dict[str, Decimal]:
    return {
        "CDI": await latest_annual_reference_pct(db, "CDI", _DEFAULT_CDI_ANNUAL_PCT),
        "SELIC": await latest_annual_reference_pct(db, "SELIC", _DEFAULT_SELIC_ANNUAL_PCT),
        "IPCA": await latest_annual_reference_pct(db, "IPCA", _DEFAULT_IPCA_ANNUAL_PCT),
        "IGPM": await latest_annual_reference_pct(db, "IGPM", _DEFAULT_IGPM_ANNUAL_PCT),
    }


def _annual_rate_pct(indexer: str, rate_pct: Decimal, refs: dict[str, Decimal]) -> Decimal:
    idx = _normalize_indexer(indexer)
    if idx == "CDI":
        pct_of_indexer = rate_pct if rate_pct > 0 else Decimal("100")
        return refs["CDI"] * pct_of_indexer / Decimal("100")
    if idx == "SELIC":
        pct_of_indexer = rate_pct if rate_pct > 0 else Decimal("100")
        return refs["SELIC"] * pct_of_indexer / Decimal("100")
    if idx == "IPCA_PLUS":
        return refs["IPCA"] + rate_pct
    if idx == "IGPM_PLUS":
        return refs["IGPM"] + rate_pct
    if idx == "PREFIXADO":
        return rate_pct
    return rate_pct


def _compound_value(principal: Decimal, annual_rate_pct: Decimal, start: date, target: date) -> Decimal:
    if principal <= 0:
        return Decimal("0")
    days = max((target - start).days, 0)
    if days == 0 or annual_rate_pct == 0:
        return principal
    annual_rate = float(annual_rate_pct / Decimal("100"))
    factor = Decimal(str((1.0 + annual_rate) ** (days / 365.0)))
    return principal * factor


async def _fallback_factor(db: AsyncSession, key: FixedIncomeKey, start: date, target: date) -> Decimal:
    refs = await _latest_refs(db)
    annual = _annual_rate_pct(key.indexer, key.rate_pct, refs)
    return _compound_value(Decimal("1"), annual, start, target)


async def _application_factor(db: AsyncSession, key: FixedIncomeKey, start: date, target: date) -> Decimal:
    idx = _normalize_indexer(key.indexer)
    try:
        if idx == "CDI":
            factor = await benchmark_factor(db, "CDI", start, target, multiplier_pct=key.rate_pct or Decimal("100"))
        elif idx == "SELIC":
            factor = await benchmark_factor(db, "SELIC", start, target, multiplier_pct=key.rate_pct or Decimal("100"))
        elif idx == "IPCA_PLUS":
            factor = await benchmark_factor(db, "IPCA", start, target, spread_annual_pct=key.rate_pct)
        elif idx == "IGPM_PLUS":
            factor = await benchmark_factor(db, "IGPM", start, target, spread_annual_pct=key.rate_pct)
        else:
            return await _fallback_factor(db, key, start, target)

        if factor != Decimal("1") or target <= start:
            return factor
        logger.warning("[fixed_income] sem histórico para %s; usando fallback anual", key)
    except Exception as exc:
        logger.warning("[fixed_income] benchmark_factor falhou para %s: %s", key, exc)

    return await _fallback_factor(db, key, start, target)


async def _load_fixed_income_transactions(db: AsyncSession, portfolio_id: int) -> list[Transaction]:
    result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id, Transaction.asset_type == RENDA_FIXA_TYPE)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    return list(result.scalars().all())


def _application_from_buy(tx: Transaction) -> FixedIncomeApplication:
    name = str(tx.ticker or "RENDA_FIXA").strip().upper()
    indexer, rate, maturity = _parse_notes(getattr(tx, "notes", None))
    amount = (
        _decimal_from_str(getattr(tx, "quantity", 0))
        * _decimal_from_str(getattr(tx, "price", 0))
        + _decimal_from_str(getattr(tx, "fees", 0))
    )
    key = FixedIncomeKey(name=name, indexer=indexer, rate_pct=_pct(rate), maturity=maturity)
    return FixedIncomeApplication(
        key=key,
        invested_amount=_money(amount),
        remaining_principal=_money(amount),
        date_start=tx.date,
    )


def _apply_redemption(applications: list[FixedIncomeApplication], tx: Transaction) -> None:
    redeem_amount = _money(
        _decimal_from_str(getattr(tx, "quantity", 0))
        * _decimal_from_str(getattr(tx, "price", 0))
    )
    if redeem_amount <= 0:
        return

    name = str(tx.ticker or "").strip().upper()
    idx, rate, maturity = _parse_notes(getattr(tx, "notes", None))
    has_full_key = bool(getattr(tx, "notes", None)) and (idx or rate or maturity)
    key = FixedIncomeKey(name=name, indexer=idx, rate_pct=_pct(rate), maturity=maturity)

    for app in applications:
        if redeem_amount <= 0:
            break
        same_product = app.key == key if has_full_key else app.key.name == name
        if not same_product or app.remaining_principal <= 0:
            continue
        consumed = min(app.remaining_principal, redeem_amount)
        app.remaining_principal -= consumed
        redeem_amount -= consumed


async def _aggregate_applications(
    db: AsyncSession,
    applications: list[FixedIncomeApplication],
    target_date: date,
) -> list[FixedIncomeValuation]:
    grouped: dict[FixedIncomeKey, dict[str, Decimal | int]] = {}

    for app in applications:
        if app.remaining_principal <= 0:
            continue
        factor = await _application_factor(db, app.key, app.date_start, target_date)
        current_value = app.remaining_principal * factor

        if app.key not in grouped:
            grouped[app.key] = {"invested": Decimal("0"), "current": Decimal("0"), "count": 0}
        grouped[app.key]["invested"] = grouped[app.key]["invested"] + app.remaining_principal  # type: ignore[operator]
        grouped[app.key]["current"] = grouped[app.key]["current"] + current_value  # type: ignore[operator]
        grouped[app.key]["count"] = int(grouped[app.key]["count"]) + 1

    result: list[FixedIncomeValuation] = []
    for key, values in grouped.items():
        invested = _money(values["invested"])  # type: ignore[arg-type]
        current = _money(values["current"])  # type: ignore[arg-type]
        income = _money(current - invested)
        income_pct = _pct((income / invested * Decimal("100")) if invested > 0 else Decimal("0"))
        result.append(
            FixedIncomeValuation(
                key=key,
                invested_amount=invested,
                current_value=current,
                income_amount=income,
                income_pct=income_pct,
                applications_count=int(values["count"]),
            )
        )

    result.sort(key=lambda item: (item.key.name, item.key.indexer, item.key.maturity or date.max))
    return result


async def get_fixed_income_valuations(
    db: AsyncSession,
    portfolio_id: int,
    target_date: Optional[date] = None,
) -> list[FixedIncomeValuation]:
    target = target_date or date.today()
    txs = await _load_fixed_income_transactions(db, portfolio_id)

    applications: list[FixedIncomeApplication] = []
    for tx in txs:
        if _is_buy(tx.operation):
            app = _application_from_buy(tx)
            if app.invested_amount > 0:
                applications.append(app)
        elif _is_sell(tx.operation):
            _apply_redemption(applications, tx)

    return await _aggregate_applications(db, applications, target)


async def get_fixed_income_totals(
    db: AsyncSession,
    portfolio_id: int,
    target_date: Optional[date] = None,
) -> dict[str, Decimal]:
    valuations = await get_fixed_income_valuations(db, portfolio_id, target_date)
    invested = _money(sum((v.invested_amount for v in valuations), Decimal("0")))
    current = _money(sum((v.current_value for v in valuations), Decimal("0")))
    income = _money(current - invested)
    income_pct = _pct((income / invested * Decimal("100")) if invested > 0 else Decimal("0"))
    return {
        "invested_amount": invested,
        "current_value": current,
        "income_amount": income,
        "income_pct": income_pct,
    }


def valuation_to_position_payload(v: FixedIncomeValuation, position_id: int) -> dict:
    maturity = v.key.maturity.isoformat() if v.key.maturity else None
    ticker = v.key.name
    display_bits = [v.key.indexer]
    if v.key.rate_pct:
        display_bits.append(f"{v.key.rate_pct}%")
    if maturity:
        display_bits.append(f"venc. {maturity}")
    asset_label = " • ".join(display_bits) or "Renda Fixa"

    return {
        "id": position_id,
        "ticker": ticker,
        "asset_type": RENDA_FIXA_TYPE,
        "asset_label": asset_label,
        "quantity": 1.0,
        "average_price": float(v.invested_amount),
        "average_price_brl": float(v.invested_amount),
        "average_price_usd": None,
        "current_price": float(v.current_value),
        "current_price_brl": float(v.current_value),
        "current_price_usd": None,
        "current_value": float(v.current_value),
        "invested_value": float(v.invested_amount),
        "variation_value": float(v.income_amount),
        "variation_percent": float(v.income_pct),
        "allocation_pct": 0.0,
        "logo_url": None,
        "is_usd": False,
        "currency": "BRL",
        "applications_count": v.applications_count,
        "maturity_date": maturity,
        "indexer": v.key.indexer,
        "rate_pct": float(v.key.rate_pct),
    }
