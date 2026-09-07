"""Shared fail-closed resolver for the synthetic certification portfolio."""
from __future__ import annotations

from sqlalchemy import select

from app.certification.portfolio_seed_contract import load_synthetic_seed_identity
from app.models.portfolio import Portfolio
from app.models.user import User, UserRole


async def load_certification_portfolio_identity(db) -> tuple[int, int]:
    """Return the unique active synthetic portfolio/user pair or fail closed."""
    identity = load_synthetic_seed_identity()
    result = await db.execute(
        select(Portfolio.id, User.id)
        .join(User, User.id == Portfolio.user_id)
        .where(
            User.email == identity.user_email,
            User.name == identity.user_name,
            User.role == UserRole.user,
            User.is_active.is_(True),
            Portfolio.name == identity.portfolio_name,
            Portfolio.description == identity.ownership_marker,
            Portfolio.is_active.is_(True),
        )
    )
    rows = list(result.all())
    if len(rows) != 1:
        raise RuntimeError("synthetic certification portfolio identity is not unique")
    return int(rows[0][0]), int(rows[0][1])
