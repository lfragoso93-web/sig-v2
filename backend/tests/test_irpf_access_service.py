from unittest.mock import AsyncMock

import pytest

from app.core.access_context import PortfolioAccessContext, PortfolioAccessDenied
from app.services.irpf_access_service import (
    READ_PORTFOLIO_IRPF,
    read_irpf_assets,
)


class _Result:
    def scalar_one_or_none(self):
        return None


@pytest.mark.asyncio
async def test_irpf_service_denies_foreign_portfolio_before_calculation(monkeypatch):
    db = AsyncMock()
    db.execute.return_value = _Result()
    calculate = AsyncMock()
    monkeypatch.setattr(
        "app.services.irpf_access_service.calc_bens_direitos", calculate
    )
    access = PortfolioAccessContext.for_user(
        user_id=55,
        portfolio_id=7,
        permissions=frozenset({READ_PORTFOLIO_IRPF}),
    )

    with pytest.raises(PortfolioAccessDenied):
        await read_irpf_assets(db, access, 2024)

    calculate.assert_not_awaited()


@pytest.mark.asyncio
async def test_irpf_service_rejects_missing_permission_before_database_query():
    db = AsyncMock()
    access = PortfolioAccessContext.for_user(
        user_id=55,
        portfolio_id=7,
        permissions=frozenset({"read:other"}),
    )

    with pytest.raises(PortfolioAccessDenied):
        await read_irpf_assets(db, access, 2024)

    db.execute.assert_not_awaited()
