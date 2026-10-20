"""Portfolio-scoped reads and writes for fixed-income contract metadata."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_context import PortfolioAccessContext
from app.models.fixed_income_contract import FixedIncomeContract
from app.repositories.portfolio_access_repository import get_accessible_portfolio
from app.schemas.fixed_income_contract import FixedIncomeContractCreate

READ_FIXED_INCOME_CONTRACTS = "read_fixed_income_contracts"
WRITE_FIXED_INCOME_CONTRACTS = "write_fixed_income_contracts"


class FixedIncomeContractNotFound(LookupError):
    """Contract is missing or outside the authorized portfolio."""


async def list_fixed_income_contracts(
    db: AsyncSession,
    access: PortfolioAccessContext,
) -> list[FixedIncomeContract]:
    await get_accessible_portfolio(
        db, access, required_permission=READ_FIXED_INCOME_CONTRACTS
    )
    result = await db.execute(
        select(FixedIncomeContract)
        .where(FixedIncomeContract.portfolio_id == access.portfolio_id)
        .order_by(FixedIncomeContract.display_name, FixedIncomeContract.id)
    )
    return list(result.scalars().all())


async def create_fixed_income_contract(
    db: AsyncSession,
    access: PortfolioAccessContext,
    payload: FixedIncomeContractCreate,
) -> FixedIncomeContract:
    await get_accessible_portfolio(
        db, access, required_permission=WRITE_FIXED_INCOME_CONTRACTS
    )
    values = payload.model_dump()
    equivalent = await db.execute(
        select(FixedIncomeContract)
        .where(
            FixedIncomeContract.portfolio_id == access.portfolio_id,
            func.lower(FixedIncomeContract.display_name)
            == values["display_name"].lower(),
            FixedIncomeContract.product_type == values["product_type"],
            FixedIncomeContract.indexer == values["indexer"],
            FixedIncomeContract.rate_value == values["rate_value"],
            FixedIncomeContract.rate_unit == values["rate_unit"],
            FixedIncomeContract.maturity_date == values["maturity_date"],
            FixedIncomeContract.liquidity_type == values["liquidity_type"],
            FixedIncomeContract.grace_period_end == values["grace_period_end"],
            FixedIncomeContract.currency == values["currency"],
        )
        .order_by(FixedIncomeContract.id)
    )
    candidates = list(equivalent.scalars().all())
    display_name = values["display_name"].lower()
    issuer_value = values["issuer"]
    candidates = [
        candidate
        for candidate in candidates
        if (
            candidate.issuer is None
            and issuer_value is None
        )
        or (
            candidate.issuer is not None
            and issuer_value is not None
            and candidate.issuer.lower() == issuer_value.lower()
        )
        or (
            candidate.issuer is not None
            and issuer_value is None
            and candidate.issuer.lower() in display_name
        )
    ]
    # Duplicates created under former manual tax metadata now resolve to the
    # lowest stable ID when all user-visible identity terms are equivalent.
    contract = candidates[0] if candidates else None
    if contract is not None:
        # Existing contracts can carry a former manual tax value or issuer field.
        # Keep the legacy issuer metadata, but refresh the now-derived tax value.
        contract.tax_exempt = values["tax_exempt"]
        return contract

    contract = FixedIncomeContract(portfolio_id=access.portfolio_id, **values)
    db.add(contract)
    await db.flush()
    return contract


async def require_fixed_income_contract(
    db: AsyncSession,
    *,
    portfolio_id: int,
    contract_id: int,
) -> FixedIncomeContract:
    result = await db.execute(
        select(FixedIncomeContract).where(
            FixedIncomeContract.id == contract_id,
            FixedIncomeContract.portfolio_id == portfolio_id,
        )
    )
    contract = result.scalar_one_or_none()
    if contract is None:
        raise FixedIncomeContractNotFound(
            "Contrato de Renda Fixa nao encontrado para esta carteira"
        )
    return contract
