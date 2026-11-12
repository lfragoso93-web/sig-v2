"""Testes para quotes_service — roteamento por tipo de ativo."""
import pytest
from unittest.mock import AsyncMock, patch

from app.services import quotes_service
from app.services.quotes_service import get_prices


BR_ITEMS = [{"ticker": "PETR4",  "asset_type": "ACAO"}]
INTL_ITEMS = [{"ticker": "AAPL",    "asset_type": "STOCK"}]
CRIPTO_ITEMS = [{"ticker": "BTC",     "asset_type": "CRIPTO"}]


@pytest.fixture(autouse=True)
def limpar_mem_cache():
    """Garante que o cache em memoria e limpo antes de cada teste."""
    quotes_service._mem_cache.clear()
    yield
    quotes_service._mem_cache.clear()


@pytest.mark.asyncio
class TestGetPrices:

    async def test_retorna_dict_vazio_sem_itens(self):
        result = await get_prices([])
        assert result == {}

    async def test_acao_nacional_vai_para_brapi(
        self,
    ):
        with patch(
            "app.services.quotes_service._fetch_brapi",
            new=AsyncMock(return_value={"PETR4": 35.5}),
        ) as mock_brapi, patch(
            "app.services.quotes_service._fetch_intl",
            new=AsyncMock(return_value={}),
        ), patch(
            "app.services.quotes_service._fetch_brapi_crypto",
            new=AsyncMock(return_value={}),
        ), patch(
            "app.services.quotes_service._fetch_yfinance",
            new=AsyncMock(return_value={}),
        ):
            result = await get_prices(BR_ITEMS)
            mock_brapi.assert_called_once()
            assert result["PETR4"] == 35.5

    async def test_stock_vai_para_yfinance(
        self,
    ):
        with patch(
            "app.services.quotes_service._fetch_brapi",
            new=AsyncMock(return_value={}),
        ), patch(
            "app.services.quotes_service._fetch_intl",
            new=AsyncMock(return_value={"AAPL": 180.0}),
        ) as mock_yf, patch(
            "app.services.quotes_service._fetch_brapi_crypto",
            new=AsyncMock(return_value={}),
        ), patch(
            "app.services.quotes_service._fetch_yfinance",
            new=AsyncMock(return_value={}),
        ):
            result = await get_prices(INTL_ITEMS)
            mock_yf.assert_called_once()
            assert result["AAPL"] == 180.0

    async def test_cripto_vai_para_brapi_crypto(
        self,
    ):
        with patch(
            "app.services.quotes_service._fetch_brapi",
            new=AsyncMock(return_value={}),
        ), patch(
            "app.services.quotes_service._fetch_intl",
            new=AsyncMock(return_value={}),
        ), patch(
            "app.services.quotes_service._fetch_brapi_crypto",
            new=AsyncMock(return_value={"BTC": 300000.0}),
        ) as mock_crypto, patch(
            "app.services.quotes_service._fetch_yfinance",
            new=AsyncMock(return_value={}),
        ):
            result = await get_prices(CRIPTO_ITEMS)
            mock_crypto.assert_called_once()
            assert result["BTC"] == 300000.0

    async def test_ticker_ausente_nao_aparece_no_resultado(
        self,
    ):
        """Se a API nao retorna o ticker, ele nao deve estar no dict final."""
        with patch(
            "app.services.quotes_service._fetch_brapi",
            new=AsyncMock(return_value={}),
        ), patch(
            "app.services.quotes_service._fetch_intl",
            new=AsyncMock(return_value={}),
        ), patch(
            "app.services.quotes_service._fetch_brapi_crypto",
            new=AsyncMock(return_value={}),
        ), patch(
            "app.services.quotes_service._fetch_yfinance",
            new=AsyncMock(return_value={}),
        ):
            result = await get_prices(BR_ITEMS)
            assert "PETR4" not in result

    async def test_mix_de_tipos_chama_todos_os_fetchers(
        self,
    ):
        items = BR_ITEMS + INTL_ITEMS + CRIPTO_ITEMS
        with patch(
            "app.services.quotes_service._fetch_brapi",
            new=AsyncMock(return_value={"PETR4": 35.0}),
        ) as mock_br, patch(
            "app.services.quotes_service._fetch_intl",
            new=AsyncMock(return_value={"AAPL": 180.0}),
        ) as mock_yf, patch(
            "app.services.quotes_service._fetch_brapi_crypto",
            new=AsyncMock(return_value={"BTC": 300000.0}),
        ) as mock_crypto, patch(
            "app.services.quotes_service._fetch_yfinance",
            new=AsyncMock(return_value={}),
        ):
            result = await get_prices(items)
            mock_br.assert_called_once()
            mock_yf.assert_called_once()
            mock_crypto.assert_called_once()
            assert len(result) == 3


@pytest.mark.asyncio
async def test_intl_uses_extended_db_ttl_and_skips_unheld_catalog_in_batch() -> None:
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    now = datetime.now(timezone.utc)
    stale_30m = now - timedelta(minutes=30)

    nvda_asset = SimpleNamespace(last_price=180.0, last_price_updated_at=stale_30m)
    petr_asset = SimpleNamespace(last_price=36.0, last_price_updated_at=stale_30m)

    def _scalar_first(obj):
        res = MagicMock()
        res.scalars.return_value.first.return_value = obj
        return res

    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[_scalar_first(nvda_asset), _scalar_first(petr_asset)]
    )

    fresh = await quotes_service._db_get_fresh_batch(
        db,
        [("NVDA", "STOCK"), ("PETR4", "ACAO")],
    )
    assert fresh == {"NVDA": 180.0}

    # Verify update_all_quotes excludes INTL_TYPES from Asset catalog scan while preserving transactions
    rows_empty = MagicMock()
    rows_empty.all.return_value = []
    db_batch = MagicMock()
    db_batch.execute = AsyncMock(side_effect=[rows_empty, rows_empty])
    db_batch.commit = AsyncMock()

    with patch("app.services.quotes_service.get_prices", new=AsyncMock(return_value={})):
        await quotes_service.update_all_quotes(db_batch)

    asset_stmt = str(db_batch.execute.await_args_list[0].args[0].compile(compile_kwargs={"literal_binds": True}))
    assert "STOCK" in asset_stmt
    assert "ETF_INTERNACIONAL" in asset_stmt
