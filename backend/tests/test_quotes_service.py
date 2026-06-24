"""Testes para quotes_service — roteamento por tipo de ativo."""
import pytest
from unittest.mock import AsyncMock, patch

from app.services import quotes_service
from app.services.quotes_service import get_prices


BR_ITEMS = [{"ticker": "PETR4",  "asset_type": "acao"}]
INTL_ITEMS = [{"ticker": "AAPL",    "asset_type": "stock"}]
CRIPTO_ITEMS = [{"ticker": "BTC",     "asset_type": "cripto"}]


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
            "app.services.quotes_service._fetch_yfinance",
            new=AsyncMock(return_value={}),
        ), patch(
            "app.services.quotes_service._fetch_brapi_crypto",
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
        ) as mock_crypto:
            result = await get_prices(CRIPTO_ITEMS)
            mock_crypto.assert_called_once()
            assert result["BTC"] == 300000.0

    async def test_ticker_ausente_nao_aparece_no_resultado(
        self,
    ):
        """Se a API nao retorna o ticker, ele nao deve estar no dict final."""
        with patch(
            "app.services.quotes_service._fetch_brapi",
            new=AsyncMock(return_value={}),  # vazio = ticker indisponivel
        ), patch(
            "app.services.quotes_service._fetch_intl",
            new=AsyncMock(return_value={}),
        ), patch(
            "app.services.quotes_service._fetch_brapi_crypto",
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
        ) as mock_crypto:
            result = await get_prices(items)
            mock_br.assert_called_once()
            mock_yf.assert_called_once()
            mock_crypto.assert_called_once()
            assert len(result) == 3
