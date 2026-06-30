"""
Snapshot diário de valor de mercado de uma carteira.

Cada registro representa o patrimônio líquido da carteira em um dia específico,
calculado com base nas cotações de fechamento dos ativos (AssetPrice).

Granularidade:
  - Um registro por carteira por dia (uq_snapshot_portfolio_date).
  - INSERT ON CONFLICT DO UPDATE → seguro para rodar múltiplas vezes no mesmo dia.

Campos calculados:
  - market_value   : valor total de mercado (Σ qty × close_price)
  - cost_basis     : custo total investido (Σ qty × avg_price) na data
  - invested_total : total aportado acumulado até a data (compras - vendas a custo)
  - realized_pnl   : lucro/prejuízo realizado acumulado até a data
  - unrealized_pnl : lucro/prejuízo não realizado = market_value - cost_basis
  - total_pnl      : realized_pnl + unrealized_pnl
  - return_pct     : total_pnl / invested_total × 100 (retorno sobre capital aportado)

Uso:
  - Gráfico de evolução patrimonial diária e mensal.
  - Cálculo de rentabilidade em qualquer janela de tempo sem recalcular transações.
  - Base para TWR (Time-Weighted Return) e outras métricas de performance.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class PortfolioSnapshot(Base, TimestampMixin):
    __tablename__ = "portfolio_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "portfolio_id", "snapshot_date",
            name="uq_snapshot_portfolio_date",
        ),
        # Sprint 5B: índice composto cobre o padrão principal de acesso:
        #   WHERE portfolio_id = X AND snapshot_date <= Y ORDER BY snapshot_date DESC
        # Usado por _snapshot_at / _latest_snapshot / _first_snapshot /
        # _snapshot_before_today sem seq scan + sort.
        # postgresql_ops define a direcionalidade apenas no PG; em SQLite é ignorado.
        Index(
            "idx_ps_portfolio_date_desc",
            "portfolio_id",
            "snapshot_date",
            postgresql_ops={"snapshot_date": "DESC"},
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # index=True removido: o índice composto acima já cobre portfolio_id
    # e snapshot_date como colunas líder, tornando os índices simples
    # redundantes e evitando overhead de manutenção dupla.
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    snapshot_date: Mapped[date] = mapped_column(
        Date, nullable=False,
        comment="Data do fechamento (dia útil ou último dado disponível).",
    )

    # ── Valores principais ──────────────────────────────────────────────────────
    market_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0"),
        comment="Valor total de mercado na data (Σ qty × close_price).",
    )
    cost_basis: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0"),
        comment="Custo total das posições abertas na data (Σ qty × avg_price).",
    )
    invested_total: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0"),
        comment="Total aportado líquido acumulado até a data (compras - resgates).",
    )

    # ── PnL ──────────────────────────────────────────────────────────────────────
    realized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0"),
        comment="Lucro/prejuízo realizado acumulado até a data.",
    )
    unrealized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0"),
        comment="Lucro/prejuízo não realizado = market_value - cost_basis.",
    )
    total_pnl: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0"),
        comment="realized_pnl + unrealized_pnl.",
    )
    return_pct: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, default=Decimal("0"),
        comment="Retorno percentual sobre capital aportado: total_pnl / invested_total × 100.",
    )

    # ── Relacionamentos ──────────────────────────────────────────────────────────
    portfolio: Mapped["Portfolio"] = relationship(
        "Portfolio", back_populates="snapshots",
    )

    def __repr__(self) -> str:
        return (
            f"<PortfolioSnapshot portfolio={self.portfolio_id} "
            f"date={self.snapshot_date} value={self.market_value}>"
        )
