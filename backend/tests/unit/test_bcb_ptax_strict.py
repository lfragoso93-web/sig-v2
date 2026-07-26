from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import httpx
import pytest

from app.integrations.bcb_ptax_strict import (
    PTAX_PAIR,
    PTAX_RATE_TYPE,
    PTAX_SOURCE,
    StrictPtaxError,
    fetch_strict_usd_brl_period,
    parse_strict_ptax_rows,
)


def test_parse_strict_ptax_rows_uses_sell_rate_and_latest_bulletin() -> None:
    rows = parse_strict_ptax_rows(
        [
            {
                "cotacaoCompra": 5.10,
                "cotacaoVenda": 5.20,
                "dataHoraCotacao": "2026-07-24 10:00:00.000",
            },
            {
                "cotacaoCompra": 5.30,
                "cotacaoVenda": 5.40,
                "dataHoraCotacao": "2026-07-24 13:00:00.000",
            },
            {
                "cotacaoVenda": 5.50,
                "dataHoraCotacao": "2026-07-25 13:00:00.000",
            },
        ]
    )

    assert len(rows) == 2
    assert rows[0].pair == PTAX_PAIR
    assert rows[0].source == PTAX_SOURCE
    assert rows[0].rate_type == PTAX_RATE_TYPE
    assert rows[0].rate_date == date(2026, 7, 24)
    assert rows[0].quoted_at == datetime(2026, 7, 24, 13, 0)
    assert rows[0].rate == Decimal("5.40")
    assert rows[1].rate == Decimal("5.50")


def test_parse_strict_ptax_rows_rejects_missing_sell_rate() -> None:
    with pytest.raises(StrictPtaxError, match="cotacaoVenda ausente"):
        parse_strict_ptax_rows(
            [
                {
                    "cotacaoCompra": 5.10,
                    "dataHoraCotacao": "2026-07-24 13:00:00.000",
                }
            ]
        )


@pytest.mark.asyncio
async def test_fetch_strict_period_uses_official_parameters() -> None:
    response = AsyncMock()
    response.raise_for_status = AsyncMock()
    response.json.return_value = {
        "value": [
            {
                "cotacaoVenda": 5.40,
                "dataHoraCotacao": "2026-07-24 13:00:00.000",
            }
        ]
    }
    client = AsyncMock()
    client.get.return_value = response

    rows = await fetch_strict_usd_brl_period(
        "2026-07-24",
        "2026-07-25",
        client=client,
    )

    assert rows[0].rate == Decimal("5.40")
    client.get.assert_awaited_once()
    url, = client.get.await_args.args
    params = client.get.await_args.kwargs["params"]
    assert url.endswith(
        "/CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"
    )
    assert params["@dataInicial"] == "'07-24-2026'"
    assert params["@dataFinalCotacao"] == "'07-25-2026'"
    assert params["$select"] == "cotacaoVenda,dataHoraCotacao"
    assert "cotacaoCompra" not in params["$select"]


@pytest.mark.asyncio
async def test_fetch_strict_period_rejects_reversed_dates() -> None:
    with pytest.raises(
        StrictPtaxError,
        match="start_date não pode ser posterior a end_date",
    ):
        await fetch_strict_usd_brl_period("2026-07-25", "2026-07-24")


@pytest.mark.asyncio
async def test_fetch_strict_period_rejects_empty_official_response() -> None:
    response = AsyncMock()
    response.raise_for_status = AsyncMock()
    response.json.return_value = {"value": []}
    client = AsyncMock()
    client.get.return_value = response

    with pytest.raises(StrictPtaxError, match="não retornou PTAX de venda"):
        await fetch_strict_usd_brl_period(
            "2026-07-24",
            "2026-07-25",
            client=client,
        )


@pytest.mark.asyncio
async def test_fetch_strict_period_wraps_http_failures() -> None:
    client = AsyncMock()
    request = httpx.Request("GET", "https://example.invalid")
    client.get.side_effect = httpx.ConnectError("offline", request=request)

    with pytest.raises(StrictPtaxError, match="falha ao consultar PTAX oficial"):
        await fetch_strict_usd_brl_period(
            "2026-07-24",
            "2026-07-25",
            client=client,
        )
