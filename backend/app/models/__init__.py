# Importa todos os models para o Alembic detectar automaticamente
from app.models.user import User
from app.models.portfolio import Portfolio
from app.models.asset import Asset
from app.models.transaction import Transaction
from app.models.portfolio_position import PortfolioPosition
from app.models.asset_dividend import AssetDividend
from app.models.dividend import Dividend, DividendType
from app.models.fixed_income import FixedIncomeInvestment
from app.models.treasury import TreasuryInvestment
from app.models.asset_price import AssetPrice
from app.models.irpf import IRPFReport
from app.models.goal import Goal
from app.models.system_config import SystemConfig
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.corporate_event import CorporateEvent, CorporateEventType, CorporateEventStatus

__all__ = [
    "User",
    "Portfolio",
    "Asset",
    "Transaction",
    "PortfolioPosition",
    "AssetDividend",
    "Dividend",
    "DividendType",
    "FixedIncomeInvestment",
    "TreasuryInvestment",
    "AssetPrice",
    "IRPFReport",
    "Goal",
    "SystemConfig",
    "PortfolioSnapshot",
    "CorporateEvent",
    "CorporateEventType",
    "CorporateEventStatus",
]
