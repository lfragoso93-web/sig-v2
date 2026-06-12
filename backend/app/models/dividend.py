"""
Dividend — provento recebido/a-receber por uma carteira especifica.
Vinculado a AssetDividend (fonte global) + portfolio.
Chave de negocio: (portfolio_id, asset_dividend_id).
"""
from sqlalchemy import (
    Integer, Float, Numeric, ForeignKey,
    Enum as SAEnum, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.portfolio import Portfolio
    from app.models.asset_dividend import AssetDividend


class DividendType(str, enum.Enum):
    DIVIDENDO   = "DIVIDENDO"
    JCP         = "JCP"
    RENDIMENTO  = "RENDIMENTO"
    AMORTIZACAO = "AMORTIZACAO"
    BONIFICACAO = "BONIFICACAO"
    OUTROS      = "OUTROS"


class DividendStatus(str, enum.Enum):
    RECEBIDO  = "RECEBIDO"
    A_RECEBER = "A_RECEBER"


class Dividend(Base):
    """
    Provento de uma carteira especifica.
    Gerado automaticamente a partir de AssetDividend quando a carteira
    possui o ativo na data-ex.
    """
    __tablename__ = "dividends"
    __table_args__ = (
        UniqueConstraint(
            "portfolio_id", "asset_dividend_id",
            name="uq_dividend_portfolio_asset_dividend"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    portfolio_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    asset_dividend_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("asset_dividends.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Quantidade de cotas do investidor na data-ex
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Valores calculados (quantity * value_per_unit)
    total_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    net_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)

    status: Mapped[DividendStatus] = mapped_column(
        SAEnum(DividendStatus),
        nullable=False,
        default=DividendStatus.A_RECEBER,
        index=True,
    )

    # Relacionamentos
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="dividends")
    asset_dividend: Mapped["AssetDividend"] = relationship(
        "AssetDividend", back_populates="portfolio_dividends"
    )

    def __repr__(self) -> str:
        return (
            f"<Dividend portfolio={self.portfolio_id} "
            f"asset_div={self.asset_dividend_id} qty={self.quantity} "
            f"status={self.status}>"
        )
