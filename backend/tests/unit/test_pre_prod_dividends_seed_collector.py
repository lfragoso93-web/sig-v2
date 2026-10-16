import inspect
from unittest.mock import AsyncMock

import pytest

import app.services.pre_prod_dividends_seed_collector as collector_module
from app.services.pre_prod_dividends_seed_collector import (
    StrictDividendAsset,
    StrictDividendCollectionError,
    StrictDividendProviderResult,
    collect_dividends_strict,
)


def _event(value: float = 1.25) -> dict:
    return {
        "lastDatePrior": "2026-07-24",
        "paymentDate": "2026-08-10",
        "rate": value,
        "label": "Dividendos",
        "eventCategory": "cash",
    }


@pytest.mark.asyncio
async def test_b3_coverage_stops_other_sources_for_listed_assets() -> None:
    calls: list[str] = []

    async def b3(ticker: str, asset_type: str):
        calls.append(f"b3:{ticker}:{asset_type}")
        return StrictDividendProviderResult(source="b3", rows=(_event(),))

    async def brapi(ticker: str, asset_type: str):
        calls.append(f"brapi:{ticker}:{asset_type}")
        return StrictDividendProviderResult(source="brapi", rows=(_event(),))

    result = await collect_dividends_strict(
        assets=(StrictDividendAsset("PETR4", "ACAO"),),
        providers=(b3, brapi),
    )

    assert calls == ["b3:PETR4:ACAO"]
    assert result[0].normalized_rows == 1
    assert result[0].sources[0].source == "b3"

@pytest.mark.asyncio
async def test_listed_asset_does_not_mix_brapi_when_b3_lacks_coverage() -> None:
    async def b3(ticker: str, asset_type: str):
        return StrictDividendProviderResult(
            source="b3",
            rows=(),
            empty_reason="provider_no_coverage",
        )

    async def brapi(ticker: str, asset_type: str):
        return StrictDividendProviderResult(
            source="brapi",
            rows=(_event(),),
        )

    result = await collect_dividends_strict(
        assets=(StrictDividendAsset("NIKE34", "BDR"),),
        providers=(b3, brapi),
    )
    assert result[0].normalized_rows == 0
    assert [source.source for source in result[0].sources] == ["b3"]


@pytest.mark.asyncio
async def test_b3_no_coverage_records_brapi_as_not_applicable() -> None:
    async def b3(ticker: str, asset_type: str):
        return StrictDividendProviderResult(
            source="b3", rows=(), empty_reason="provider_no_coverage",
        )

    async def brapi(ticker: str, asset_type: str):
        return StrictDividendProviderResult(source="brapi", rows=(_event(),))

    result = await collect_dividends_strict(
        assets=(StrictDividendAsset("PETR4", "ACAO"),),
        providers=(b3, brapi),
    )
    assert result[0].normalized_rows == 0
    assert [source.source for source in result[0].sources] == ["b3"]

@pytest.mark.asyncio
async def test_yahoo_is_rejected_for_listed_asset_even_after_b3_empty() -> None:
    async def b3(ticker: str, asset_type: str):
        return StrictDividendProviderResult(
            source="b3", rows=(), empty_reason="provider_no_coverage",
        )

    async def yahoo(ticker: str, asset_type: str):
        return StrictDividendProviderResult(source="yfinance_history", rows=(_event(),))

    result = await collect_dividends_strict(
        assets=(StrictDividendAsset("PETR4", "ACAO"),),
        providers=(b3, yahoo),
    )
    assert result[0].normalized_rows == 0
    assert [source.source for source in result[0].sources] == ["b3"]

@pytest.mark.asyncio
async def test_provider_failure_is_blocking_and_stops_next_source() -> None:
    async def unavailable(ticker: str, asset_type: str):
        raise RuntimeError("timeout")

    next_provider = AsyncMock()

    with pytest.raises(
        StrictDividendCollectionError,
        match="provedor unavailable indisponível",
    ):
        await collect_dividends_strict(
            assets=(StrictDividendAsset("PETR4", "ACAO"),),
            providers=(unavailable, next_provider),
        )

    next_provider.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_payload_is_blocking_instead_of_silently_discarded() -> None:
    async def b3(ticker: str, asset_type: str):
        return StrictDividendProviderResult(
            source="b3",
            rows=({"rate": 1.0, "label": "Dividendos"},),
        )

    with pytest.raises(StrictDividendCollectionError, match="1 linha"):
        await collect_dividends_strict(
            assets=(StrictDividendAsset("PETR4", "ACAO"),),
            providers=(b3,),
        )


def test_empty_provider_payload_requires_explicit_reason() -> None:
    with pytest.raises(ValueError, match="empty_reason"):
        StrictDividendProviderResult(source="b3", rows=())


@pytest.mark.parametrize(
    "asset_type",
    ["CRIPTO", "TESOURO_DIRETO", "RENDA_FIXA", "ETF_INTERNACIONAL"],
)
def test_rejects_asset_types_outside_operational_boundary(
    asset_type: str,
) -> None:
    with pytest.raises(ValueError, match="inelegível"):
        StrictDividendAsset("TEST", asset_type)


@pytest.mark.asyncio
async def test_requires_explicit_provider_list() -> None:
    with pytest.raises(ValueError, match="provedor"):
        await collect_dividends_strict(
            assets=(StrictDividendAsset("PETR4", "ACAO"),),
            providers=(),
        )


def test_collector_has_no_database_or_concurrency_port() -> None:
    source = inspect.getsource(collector_module)

    for forbidden in (
        "AsyncSession",
        "asyncio.gather",
        "create_task",
        ".commit(",
        ".rollback(",
        ".flush(",
        ".delete(",
    ):
        assert forbidden not in source
