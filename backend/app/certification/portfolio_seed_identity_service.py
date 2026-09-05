"""Canonical provisioning for the synthetic certification user and portfolio."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.certification.portfolio_seed_contract import (
    SyntheticSeedContractError,
    load_synthetic_seed_identity,
)
from app.core.security import verify_password
from app.models.portfolio import Portfolio
from app.models.user import User, UserRole
from app.schemas.portfolio import PortfolioCreate
from app.schemas.user import UserCreate
from app.services import portfolio_service, user_service


class SyntheticSeedIdentityError(SyntheticSeedContractError):
    """Raised when an existing user/portfolio cannot be proven synthetic-owned."""


@dataclass(frozen=True)
class SyntheticSeedProvisionResult:
    user_id: int
    portfolio_id: int
    user_created: bool
    portfolio_created: bool


def _assert_owned_user(user: User, password: str) -> None:
    identity = load_synthetic_seed_identity()
    if user.email != identity.user_email:
        raise SyntheticSeedIdentityError("synthetic user email does not match reserved identity")
    if user.name != identity.user_name:
        raise SyntheticSeedIdentityError("reserved synthetic email belongs to a different user name")
    if user.role != UserRole.user:
        raise SyntheticSeedIdentityError("synthetic certification user must keep role=user")
    if user.is_active is not True:
        raise SyntheticSeedIdentityError("synthetic certification user must remain active")
    if not verify_password(password, user.hashed_password):
        raise SyntheticSeedIdentityError("synthetic certification password does not match existing user")


def _assert_owned_portfolio(portfolio: Portfolio) -> None:
    identity = load_synthetic_seed_identity()
    if portfolio.name != identity.portfolio_name:
        raise SyntheticSeedIdentityError("synthetic portfolio name does not match reserved identity")
    if portfolio.description != identity.ownership_marker:
        raise SyntheticSeedIdentityError("synthetic portfolio ownership marker does not match")


async def _load_reserved_portfolios(db: AsyncSession) -> list[Portfolio]:
    identity = load_synthetic_seed_identity()
    result = await db.execute(
        select(Portfolio).where(Portfolio.name == identity.portfolio_name)
    )
    return list(result.scalars().all())


async def provision_synthetic_user_portfolio(
    db: AsyncSession,
    *,
    password: str,
) -> SyntheticSeedProvisionResult:
    """Create or reuse only the exact disposable identity reserved by issue #303.

    The password is intentionally supplied by the caller so no reusable credential is
    embedded in the repository. Existing state is accepted only when ownership can be
    proven without mutating it.
    """
    identity = load_synthetic_seed_identity()
    user_data = UserCreate(
        name=identity.user_name,
        email=identity.user_email,
        password=password,
    )

    existing_user = await user_service.get_user_by_email(db, identity.user_email)
    reserved_portfolios = await _load_reserved_portfolios(db)

    if existing_user is None:
        if reserved_portfolios:
            raise SyntheticSeedIdentityError(
                "reserved synthetic portfolio name already belongs to another user"
            )

        user = await user_service.create_user(db, user_data, role=UserRole.user)
        portfolio = await portfolio_service.create_portfolio(
            db,
            user.id,
            PortfolioCreate(
                name=identity.portfolio_name,
                description=identity.ownership_marker,
            ),
        )
        return SyntheticSeedProvisionResult(
            user_id=user.id,
            portfolio_id=portfolio.id,
            user_created=True,
            portfolio_created=True,
        )

    _assert_owned_user(existing_user, password)

    user_portfolios = await portfolio_service.list_portfolios(db, existing_user.id)
    if len(user_portfolios) > 1:
        raise SyntheticSeedIdentityError(
            "synthetic certification user has extra portfolios; ownership is ambiguous"
        )
    if user_portfolios:
        portfolio = user_portfolios[0]
        _assert_owned_portfolio(portfolio)
        if any(row.id != portfolio.id for row in reserved_portfolios):
            raise SyntheticSeedIdentityError(
                "reserved synthetic portfolio name is also used by another portfolio"
            )
        return SyntheticSeedProvisionResult(
            user_id=existing_user.id,
            portfolio_id=portfolio.id,
            user_created=False,
            portfolio_created=False,
        )

    if reserved_portfolios:
        raise SyntheticSeedIdentityError(
            "reserved synthetic portfolio name already belongs to another user"
        )

    portfolio = await portfolio_service.create_portfolio(
        db,
        existing_user.id,
        PortfolioCreate(
            name=identity.portfolio_name,
            description=identity.ownership_marker,
        ),
    )
    return SyntheticSeedProvisionResult(
        user_id=existing_user.id,
        portfolio_id=portfolio.id,
        user_created=False,
        portfolio_created=True,
    )
