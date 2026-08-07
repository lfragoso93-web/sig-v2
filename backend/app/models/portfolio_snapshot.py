"""
Snapshot diário de valor de mercado e performance de uma carteira.

Cada registro representa o fechamento financeiro de uma carteira em uma data,
calculado a partir das posições, preços históricos, fluxos externos e proventos.

Granularidade:
  - Um registro por carteira por dia (uq_snapshot_portfolio_date).
  - INSERT ON CONFLICT DO UPDATE, seguro para reprocessamentos.

Os campos ``daily_return_pct`` e ``accumulated_return_pct`` armazenam retorno
ponderado pelo tempo (TWR). Enquanto a carteira não possuir fluxos externos
explícitos, ``return_is_estimated`` permanece verdadeiro para deixar claro que
os valores dependem de inferência transitória.
"""
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Index, Numeric, UniqueConstraint, desc
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.portfolio import Portfolio


class PortfolioSnapshot(Base, TimestampMixin):
    __tablename__ = "portfolio_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "portfolio_id", "snapshot_date",
            name="uq_snapshot_portfolio_date",
        ),
        Index("ix_portfolio_snapshots_portfolio_id", "portfolio_id"),
        Index("ix_portfolio_snapshots_snapshot_date", "snapshot_date"),
        Index(
            "ix_portfolio_snapshots_portfolio_date",
            "portfolio_id",
            "snapshot_date",
        ),
        Index(
            "idx_ps_portfolio_date_desc",
            "portfolio_id",
            desc("snapshot_date"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    snapshot_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Data do fechamento (dia útil ou último dado disponível).",
    )

    # Valores principais
    market_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0"),
        comment="Valor total de mercado na data (Σ qty × close_price).",
    )
    cost_basis: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0"),
        comment="Custo total das posições abertas (Σ qty × avg_price).",
    )
    invested_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0"),
        comment="Total aportado líquido acumulado até a data.",
    )

    # Resultado
    realized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0"),
        comment="Lucro/prejuízo realizado acumulado até a data.",
    )
    unrealized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0"),
        comment="market_value - cost_basis.",
    )
    total_pnl: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0"),
        comment="realized_pnl + unrealized_pnl.",
    )
    return_pct: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        nullable=False,
        default=Decimal("0"),
        comment="total_pnl / invested_total × 100.",
    )

    # Fluxos, proventos e TWR. A migration 20260713 adicionou estes campos
    # sem comentários de coluna; a semântica permanece documentada aqui.
    net_external_flow: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0"),
    )
    dividends_day: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0"),
    )
    dividends_accumulated: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0"),
    )
    daily_return_pct: Mapped[Decimal] = mapped_column(
        Numeric(12, 6),
        nullable=False,
        default=Decimal("0"),
    )
    accumulated_return_pct: Mapped[Decimal] = mapped_column(
        Numeric(12, 6),
        nullable=False,
        default=Decimal("0"),
    )
    has_partial_prices: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    return_is_estimated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    portfolio: Mapped["Portfolio"] = relationship(
        "Portfolio",
        back_populates="snapshots",
    )

    def __repr__(self) -> str:
        return (
            f"<PortfolioSnapshot portfolio={self.portfolio_id} "
            f"date={self.snapshot_date} value={self.market_value}>"
        )
