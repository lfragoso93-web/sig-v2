from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.routers.portfolios import _localize_csv_message, import_portfolio_csv
from app.services.csv_import_service import import_transactions_csv


class FakeUpload:
    def __init__(self, content: bytes):
        self._content = content

    async def read(self) -> bytes:
        return self._content


@pytest.mark.asyncio
async def test_import_upload_rejects_empty_file():
    db = AsyncMock(spec=AsyncSession)

    result = await import_transactions_csv(
        db=db,
        portfolio_id=1,
        user_id=1,
        file=FakeUpload(b""),
        dry_run=True,
    )

    assert result["success"] is False
    assert result["error_count"] == 1
    assert result["global_errors"] == ["O arquivo CSV está vazio"]


@pytest.mark.asyncio
async def test_import_upload_dry_run_validates_without_persisting():
    db = AsyncMock(spec=AsyncSession)
    portfolio_result = AsyncMock()
    portfolio_result.scalar_one_or_none.return_value = SimpleNamespace(id=1, user_id=7)
    db.execute.return_value = portfolio_result

    csv = (
        "ticker,asset_type,operation,quantity,price,date,fees,currency,notes\n"
        "PETR4,ACAO,buy,10,30.00,2024-01-10,0,BRL,teste\n"
    ).encode("utf-8")

    with patch(
        "app.services.csv_import_service.import_csv_transactions",
        new_callable=AsyncMock,
    ) as persist:
        result = await import_transactions_csv(
            db=db,
            portfolio_id=1,
            user_id=7,
            file=FakeUpload(csv),
            dry_run=True,
        )

    assert result["success"] is True
    assert result["imported_count"] == 0
    assert result["error_count"] == 0
    assert result["rows"][0]["status"] == "valid"
    persist.assert_not_awaited()


@pytest.mark.asyncio
async def test_import_upload_delegates_when_not_dry_run():
    db = AsyncMock(spec=AsyncSession)
    csv = (
        "ticker,asset_type,operation,quantity,price,date,fees,currency,notes\n"
        "PETR4,ACAO,buy,10,30.00,2024-01-10,0,BRL,teste\n"
    ).encode("utf-8")
    expected = {
        "success": True,
        "imported_count": 1,
        "skipped_count": 0,
        "error_count": 0,
        "rows": [],
        "global_errors": [],
    }

    with patch(
        "app.services.csv_import_service.import_csv_transactions",
        new_callable=AsyncMock,
        return_value=expected,
    ) as persist:
        result = await import_transactions_csv(
            db=db,
            portfolio_id=3,
            user_id=9,
            file=FakeUpload(csv),
            dry_run=False,
        )

    assert result == expected
    persist.assert_awaited_once()
    kwargs = persist.await_args.kwargs
    assert kwargs["portfolio_id"] == 3
    assert kwargs["user_id"] == 9
    assert "PETR4" in kwargs["content"]


def test_csv_messages_are_localized():
    assert _localize_csv_message("ticker is required") == "O campo ticker é obrigatório"
    assert _localize_csv_message(
        "Missing required headers: price, date"
    ) == "Colunas obrigatórias ausentes: price, date"
    assert "não suportado" in _localize_csv_message(
        "asset_type 'INVALIDO' not supported. Valid: ACAO, FII"
    )


@pytest.mark.asyncio
async def test_router_refreshes_caches_after_real_import():
    db = AsyncMock(spec=AsyncSession)
    current_user = SimpleNamespace(id=11)
    service_result = {
        "success": True,
        "imported_count": 2,
        "skipped_count": 0,
        "error_count": 0,
        "rows": [],
        "global_errors": [],
    }

    with patch(
        "app.routers.portfolios.get_portfolio",
        new_callable=AsyncMock,
    ) as get_portfolio, patch(
        "app.routers.portfolios.csv_import_service.import_transactions_csv",
        new_callable=AsyncMock,
        return_value=service_result,
    ), patch(
        "app.routers.portfolios.invalidate_portfolio_cache",
        new_callable=AsyncMock,
    ) as invalidate, patch(
        "app.routers.portfolios.flush_rentabilidade_cache",
        new_callable=AsyncMock,
    ) as flush_rentabilidade:
        result = await import_portfolio_csv(
            portfolio_id=5,
            file=FakeUpload(b"csv"),
            dry_run=False,
            db=db,
            current_user=current_user,
        )

    get_portfolio.assert_awaited_once_with(db, 5, 11)
    invalidate.assert_awaited_once_with(5)
    flush_rentabilidade.assert_awaited_once_with(5)
    assert result["imported_count"] == 2
