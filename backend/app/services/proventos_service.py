from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_
from app.models.dividend import Dividend, DividendStatus
from app.models.asset import Asset
from app.schemas.dividend import (
    ProventosSummary, ProventoDistribution,
    ProventosEvolucao, ProventosHistoricoMes, ProventoItem
)
from typing import Optional
import calendar


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

    # Total carteira (todos os recebidos)
    total_carteira = db.query(func.sum(Dividend.net_value)).filter(
        Dividend.portfolio_id == portfolio_id,
        Dividend.status == DividendStatus.RECEBIDO,
    ).scalar() or 0.0

    # Total últimos 12 meses (recebidos)
    total_12m = db.query(func.sum(Dividend.net_value)).filter(
        Dividend.portfolio_id == portfolio_id,
        Dividend.status == DividendStatus.RECEBIDO,
        Dividend.payment_date >= start_12m,
    ).scalar() or 0.0

    media_mensal = total_12m / 12

    return ProventosSummary(
        media_mensal=float(media_mensal),
        meta_mensal=0.0,
        meta_percent=0.0,
        total_12m=float(total_12m),
        total_carteira=float(total_carteira),
    )


def get_distribution(db: Session, portfolio_id: int, months: int = 12) -> list[ProventoDistribution]:
    start = date.today() - relativedelta(months=months)
    rows = (
        db.query(Asset.ticker, func.sum(Dividend.net_value).label("total"))
        .join(Dividend, Dividend.asset_id == Asset.id)
        .filter(
            Dividend.portfolio_id == portfolio_id,
            Dividend.payment_date >= start,
        )
        .group_by(Asset.ticker)
        .order_by(func.sum(Dividend.net_value).desc())
        .all()
    )
    grand_total = sum(r.total for r in rows) or 1
    return [
        ProventoDistribution(
            ticker=r.ticker,
            total=float(r.total),
            percentage=float(r.total / grand_total * 100),
        )
        for r in rows
    ]


def get_evolucao(
    db: Session, portfolio_id: int, tipo: str, period: str,
    asset_type: Optional[str] = None,
) -> list[ProventosEvolucao]:
    start = _period_start(period)
    filters = [Dividend.portfolio_id == portfolio_id, Dividend.payment_date >= start]
    if asset_type:
        filters.append(Asset.asset_type == asset_type)

    base_q = (
        db.query(
            Dividend.payment_date,
            Dividend.net_value,
            Dividend.status,
        )
        .join(Asset, Asset.id == Dividend.asset_id)
        .filter(and_(*filters))
        .all()
    )

    # Agrupa por mês ou ano
    buckets: dict[str, dict] = {}
    for row in base_q:
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
    db: Session, portfolio_id: int,
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
            extract("year", Dividend.payment_date).label("year"),
            extract("month", Dividend.payment_date).label("month"),
            func.sum(Dividend.net_value).label("total"),
        )
        .join(Asset, Asset.id == Dividend.asset_id)
        .filter(and_(*filters))
        .group_by("year", "month")
        .order_by("year", "month")
        .all()
    )

    # Monta dicionário year -> {month -> total}
    data: dict[int, dict[int, float]] = {}
    for r in rows:
        y, m = int(r.year), int(r.month)
        data.setdefault(y, {})[m] = float(r.total)

    result = []
    for year in sorted(data.keys(), reverse=True):
        months_vals = [data[year].get(m) for m in range(1, 13)]
        values = [v for v in months_vals if v is not None]
        total = sum(values)
        media = total / len(values) if values else 0
        result.append(ProventosHistoricoMes(
            year=year,
            months=months_vals,
            total=total,
            media=media,
        ))
    return result


def get_list(
    db: Session, portfolio_id: int,
    year: Optional[int] = None,
    status: Optional[str] = None,
    asset_type: Optional[str] = None,
) -> list[ProventoItem]:
    filters = [Dividend.portfolio_id == portfolio_id]
    if year:
        filters.append(extract("year", Dividend.payment_date) == year)
    if status:
        filters.append(Dividend.status == status)
    if asset_type:
        filters.append(Asset.asset_type == asset_type)

    rows = (
        db.query(Dividend, Asset)
        .join(Asset, Asset.id == Dividend.asset_id)
        .filter(and_(*filters))
        .order_by(Dividend.payment_date.desc())
        .all()
    )

    return [
        ProventoItem(
            id=d.id,
            ticker=a.ticker,
            asset_type=a.asset_type,
            dividend_type=d.dividend_type,
            status=d.status,
            ex_date=d.ex_date,
            payment_date=d.payment_date,
            quantity=float(d.quantity),
            value_per_unit=float(d.value_per_unit),
            total_value=float(d.total_value),
            net_value=float(d.net_value),
        )
        for d, a in rows
    ]
