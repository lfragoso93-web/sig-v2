from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.treasury_catalog_query_service import (
    get_persisted_treasury_commercial_names,
)


@pytest.mark.asyncio
async def test_commercial_names_are_loaded_in_one_db_query() -> None:
    db = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.all.return_value = [
        SimpleNamespace(
            ticker="tesouro-renda-mais-15122079",
            commercial_name="Tesouro RendA+ Aposentadoria Extra 15/12/2079",
            legacy_name="Nome legado",
        )
    ]
    db.execute.return_value = result

    names = await get_persisted_treasury_commercial_names(
        db,
        ["TESOURO-RENDA-MAIS-15122079", "tesouro-renda-mais-15122079"],
    )

    assert names == {
        "tesouro-renda-mais-15122079": (
            "Tesouro RendA+ Aposentadoria Extra 15/12/2079"
        )
    }
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_commercial_names_fall_back_to_legacy_asset_name() -> None:
    db = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.all.return_value = [
        SimpleNamespace(
            ticker="tesouro-selic-01032031",
            commercial_name=None,
            legacy_name="Tesouro Selic 2031",
        )
    ]
    db.execute.return_value = result

    names = await get_persisted_treasury_commercial_names(
        db,
        ["tesouro-selic-01032031"],
    )

    assert names == {"tesouro-selic-01032031": "Tesouro Selic 2031"}


@pytest.mark.asyncio
async def test_commercial_names_skip_empty_symbols_without_query() -> None:
    db = AsyncMock(spec=AsyncSession)

    assert await get_persisted_treasury_commercial_names(db, ["", " "]) == {}
    db.execute.assert_not_awaited()
