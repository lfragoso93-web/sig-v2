from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_context import PortfolioAccessContext, PortfolioAccessDenied
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.fixed_income_contract import (
    FixedIncomeContractCreate,
    FixedIncomeContractOut,
)
from app.services.fixed_income_contract_service import (
    READ_FIXED_INCOME_CONTRACTS,
    WRITE_FIXED_INCOME_CONTRACTS,
    create_fixed_income_contract,
    list_fixed_income_contracts,
)

router = APIRouter()


def _access(portfolio_id: int, user: User, permission: str) -> PortfolioAccessContext:
    return PortfolioAccessContext.for_user(
        user_id=user.id,
        portfolio_id=portfolio_id,
        permissions=frozenset({permission}),
    )


@router.get(
    "/{portfolio_id}/fixed-income-contracts",
    response_model=list[FixedIncomeContractOut],
)
async def get_fixed_income_contracts(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await list_fixed_income_contracts(
            db,
            _access(portfolio_id, current_user, READ_FIXED_INCOME_CONTRACTS),
        )
    except PortfolioAccessDenied as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/{portfolio_id}/fixed-income-contracts",
    response_model=FixedIncomeContractOut,
    status_code=status.HTTP_201_CREATED,
)
async def post_fixed_income_contract(
    portfolio_id: int,
    payload: FixedIncomeContractCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        contract = await create_fixed_income_contract(
            db,
            _access(portfolio_id, current_user, WRITE_FIXED_INCOME_CONTRACTS),
            payload,
        )
        await db.commit()
        await db.refresh(contract)
        return contract
    except PortfolioAccessDenied as exc:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
