import httpx
import pytest

from app.integrations.brapi_v2_client import BrapiV2Client, BrapiV2Error
from app.services.ticker_resolution_service import TickerResolutionService


@pytest.mark.asyncio
async def test_client_normaliza_falha_de_rede() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    client = BrapiV2Client(base_url="https://market.example/api")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        with pytest.raises(BrapiV2Error, match="comunicacao"):
            await client.resolve_tickers(["PETR4"], client=http_client)


@pytest.mark.asyncio
async def test_client_rejeita_json_invalido() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

    client = BrapiV2Client(base_url="https://market.example/api")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        with pytest.raises(BrapiV2Error, match="Resposta invalida"):
            await client.resolve_tickers(["PETR4"], client=http_client)


class FailingClient:
    async def resolve_tickers(self, symbols: list[str]):
        raise BrapiV2Error("provider unavailable")


@pytest.mark.asyncio
async def test_service_mantem_ticker_quando_provider_indisponivel() -> None:
    service = TickerResolutionService(client=FailingClient())  # type: ignore[arg-type]

    result = await service.resolve_many(["PETR4"])

    assert result["PETR4"].current_ticker == "PETR4"
    assert result["PETR4"].changed is False
    assert result["PETR4"].status == "unavailable"
