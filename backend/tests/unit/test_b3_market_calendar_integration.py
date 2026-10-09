import httpx
import pytest

from app.integrations.b3_market_calendar import fetch_b3_annual_calendar_page


@pytest.mark.asyncio
async def test_rejects_non_official_b3_calendar_host() -> None:
    with pytest.raises(ValueError, match="official HTTPS host"):
        await fetch_b3_annual_calendar_page("https://example.test/calendar")


@pytest.mark.asyncio
async def test_fetches_bounded_official_b3_calendar_page() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "www.b3.com.br"
        return httpx.Response(
            200,
            text="01 de janeiro - Confraternização",
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        text = await fetch_b3_annual_calendar_page(
            "https://www.b3.com.br/pt_br/noticias/calendario-2026.htm",
            client=client,
        )

    assert text == "01 de janeiro - Confraternização"
