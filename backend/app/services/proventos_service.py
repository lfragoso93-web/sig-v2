from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_
from app.models.dividend import Dividend, DividendStatus
from app.models.asset_dividend import AssetDividend
from app.models.asset import Asset
from app.schemas.dividend import (
    ProventosSummary, ProventoDistribution,
    ProventosEvolucao, ProventosHistoricoMes, ProventoItem
)
from typing import Optional


def _period_start(period: str) -> date:
    today = date.today()
    if period == "12m":
        return today - relativedelta(months=12)
    elif period == "24m":
        return today - relativedelta(months=24)
    elif period == "ytd":
        return date(today.year, 1, 1)
    else:
        return date(2000, 1, 1)


def get_summary(db: Session, portfolio_id: int) -> ProventosSummary:
    today = date.today()
    start_12m = today - relativedelta(months=12)

    base = (
        db.query(Dividend)
        .join(AssetDividend, AssetDividend.id == Dividend.asset_dividend_id)
        .filter(Dividend.portfolio_id == portfolio_id)
    )

    total_carteira = (
        base.filter(Dividend.status == DividendStatus.RECEBIDO)
        .with_entities(func.sum(Dividend.net_value))
        .scalar() or 0.0
    )

    total_12m = (
        base.filter(
            Dividend.status == DividendStatus.RECEBIDO,
            AssetDividend.payment_date >= start_12m,
        )
        .with_entities(func.sum(Dividend.net_value))
        .scalar() or 0.0
    )

    media_mensal = float(total_12m) / 12

    return ProventosSummary(
        media_mensal=media_mensal,
        meta_mensal=0.0,
        meta_percent=0.0,
        total_12m=float(total_12m),
        total_carteira=float(total_carteira),
    )


def get_distribution(
    db: Session, portfolio_id: int, months: int = 12
) -> list[ProventoDistribution]:
    start = date.today() - relativedelta(months=months)

    rows = (
        db.query(Asset.ticker, func.sum(Dividend.net_value).label("total"))
        .join(AssetDividend, AssetDividend.id == Dividend.asset_dividend_id)
        .join(Asset, Asset.id == AssetDividend.asset_id)
        .filter(
            Dividend.portfolio_id == portfolio_id,
            AssetDividend.payment_date >= start,
        )
        .group_by(Asset.ticker)
        .order_by(func.sum(Dividend.net_value).desc())
        .all()
    )

    grand_total = sum(float(r.total) for r in rows) or 1.0
    return [
        ProventoDistribution(
            ticker=r.ticker,
            total=float(r.total),
            percentage=float(r.total) / grand_total * 100,
        )
        for r in rows
    ]


def get_evolucao(
    db: Session,
    portfolio_id: int,
    tipo: str,
    period: str,
    asset_type: Optional[str] = None,
) -> list[ProventosEvolucao]:
    start = _period_start(period)

    filters = [
        Dividend.portfolio_id == portfolio_id,
        AssetDividend.payment_date >= start,
    ]
    if asset_type:
        filters.append(Asset.asset_type == asset_type)

    rows = (
        db.query(
            AssetDividend.payment_date,
            Dividend.net_value,
            Dividend.status,
        )
        .join(AssetDividend, AssetDividend.id == Dividend.asset_dividend_id)
        .join(Asset, Asset.id == AssetDividend.asset_id)
        .filter(and_(*filters))
        .all()
    )

    buckets: dict[str, dict] = {}
    for row in rows:
        if row.payment_date is None:
            continue
        key = (
            row.payment_date.strftime("%b/%Y") if tipo == "mensal"
            else str(row.payment_date.year)
        )
        if key not in buckets:
            buckets[key] = {"recebido": 0.0, "a_receber": 0.0}
        if row.status == DividendStatus.RECEBIDO:
            buckets[key]["recebido"] += float(row.net_value)
        else:
            buckets[key]["a_receber"] += float(row.net_value)

    return [
        ProventosEvolucao(month=k, recebido=v["recebido"], a_receber=v["a_receber"])
        for k, v in buckets.items()
    ]


def get_historico_mensal(
    db: Session,
    portfolio_id: int,
    status: Optional[str] = None,
    asset_type: Optional[str] = None,
) -> list[ProventosHistoricoMes]:
    filters = [Dividend.portfolio_id == portfolio_id]
    if status:
        filters.append(Dividend.status == status)
    if asset_type:
        filters.append(Asset.asset_type == asset_type)

    rows = (
        db.query(
            extract("year",  AssetDividend.payment_date).label("year"),
            extract("month", AssetDividend.payment_date).label("month"),
            func.sum(Dividend.net_value).label("total"),
        )
        .join(AssetDividend, AssetDividend.id == Dividend.asset_dividend_id)
        .join(Asset, Asset.id == AssetDividend.asset_id)
        .filter(and_(*filters))
        .group_by("year", "month")
        .order_by("year", "month")
        .all()
    )

    data: dict[int, dict[int, float]] = {}
    for r in rows:
        y, m = int(r.year), int(r.month)
        data.setdefault(y, {})[m] = float(r.total)

    result = []
    for year in sorted(data.keys(), reverse=True):
        months_vals = [data[year].get(m) for m in range(1, 13)]
        values = [v for v in months_vals if v is not None]
        total  = sum(values)
        media  = total / len(values) if values else 0.0
        result.append(ProventosHistoricoMes(
            year=year,
            months=months_vals,
            total=total,
            media=media,
        ))
    return result


def get_list(
    db: Session,
    portfolio_id: int,
    year: Optional[int] = None,
    status: Optional[str] = None,
    asset_type: Optional[str] = None,
) -> list[ProventoItem]:
    filters = [Dividend.portfolio_id == portfolio_id]
    if year:
        filters.append(extract("year", AssetDividend.payment_date) == year)
    if status:
        filters.append(Dividend.status == status)
    if asset_type:
        filters.append(Asset.asset_type == asset_type)

    rows = (
        db.query(Dividend, AssetDividend, Asset)
        .join(AssetDividend, AssetDividend.id == Dividend.asset_dividend_id)
        .join(Asset, Asset.id == AssetDividend.asset_id)
        .filter(and_(*filters))
        .order_by(AssetDividend.payment_date.desc())
        .all()
    )

    return [
        ProventoItem(
            id=d.id,
            ticker=a.ticker,
            asset_type=a.asset_type,
            dividend_type=ad.dividend_type,
            status=d.status,
            ex_date=ad.ex_date,
            payment_date=ad.payment_date,
            quantity=float(d.quantity),
            value_per_unit=float(ad.value_per_unit),
            total_value=float(d.total_value) if d.total_value else 0.0,
            net_value=float(d.net_value) if d.net_value else 0.0,
        )
        for d, ad, a in rows
    ]
