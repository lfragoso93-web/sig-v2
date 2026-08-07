from sqlalchemy import String, ForeignKey, Index, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.portfolio import Portfolio


class PortfolioClassTarget(Base, TimestampMixin):
    """
    Meta de alocação por classe de ativo definida pelo usuário.
    Ex: ACAO -> 40%, FII -> 20%.
    """
    __tablename__ = 'portfolio_class_targets'
    __table_args__ = (
        UniqueConstraint('portfolio_id', 'asset_type', name='uq_portfolio_class_target'),
        Index('idx_pct_portfolio', 'portfolio_id'),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey('portfolios.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)

    portfolio: Mapped['Portfolio'] = relationship('Portfolio', back_populates='class_targets')

    def __repr__(self) -> str:
        return f'<PortfolioClassTarget portfolio_id={self.portfolio_id} asset_type={self.asset_type} target_pct={self.target_pct}>'
