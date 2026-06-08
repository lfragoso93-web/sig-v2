# Importa todos os models para o Alembic detectar automaticamente
from app.models.user import User
from app.models.portfolio import Portfolio
from app.models.asset import Asset
from app.models.transaction import Transaction
from app.models.portfolio_position import PortfolioPosition
from app.models.dividend import Dividend
from app.models.fixed_income import FixedIncomeInvestment
from app.models.treasury import TreasuryInvestment
from app.models.asset_price import AssetPrice
from app.models.irpf import IRPFRecord, IRPFLoss
from app.models.goal import Goal, GoalAllocation
from app.models.system_config import SystemConfig

__all__ = [
    "User",
    "Portfolio",
    "Asset",
    "Transaction",
    "PortfolioPosition",
    "Dividend",
    "FixedIncomeInvestment",
    "TreasuryInvestment",
    "AssetPrice",
    "IRPFRecord",
    "IRPFLoss",
    "Goal",
    "GoalAllocation",
    "SystemConfig",
]
