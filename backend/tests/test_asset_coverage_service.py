import pytest
from app.services.asset_coverage_service import (
    AssetCoverageService,
    CAPABILITY_HISTORY,
    CAPABILITY_DIVIDENDS,
    CAPABILITY_QUOTE,
    STATUS_FULL,
    STATUS_PARTIAL,
    STATUS_UNSUPPORTED,
    TTL_SUPPORTED,
    TTL_UNSUPPORTED,
    TTL_TRANSIENT_ERROR,
)


@pytest.fixture
def service():
    # Retorna uma instancia limpa e isolada do servico
    return AssetCoverageService()


@pytest.mark.asyncio
async def test_is_supported_fail_open_for_unknown_ticker(service: AssetCoverageService):
    # Ticker nunca consultado deve ser fail-open (True) para permitir descoberta inicial
    assert await service.is_supported("PETR4", CAPABILITY_HISTORY) is True
    assert await service.is_supported("PETR4", CAPABILITY_DIVIDENDS) is True


@pytest.mark.asyncio
async def test_record_capability_supported_and_status_full(service: AssetCoverageService):
    report = await service.record_capability("VALE3", CAPABILITY_HISTORY, supported=True)
    assert report.ticker == "VALE3"
    assert report.status == STATUS_FULL
    assert report.capabilities[CAPABILITY_HISTORY] is True
    assert report.ttl_seconds == TTL_SUPPORTED

    # is_supported confirma True
    assert await service.is_supported("VALE3", CAPABILITY_HISTORY) is True


@pytest.mark.asyncio
async def test_record_capability_unsupported_blocks_calls(service: AssetCoverageService):
    report = await service.record_capability(
        "FAKE4", CAPABILITY_HISTORY, supported=False, error_code="404_NOT_FOUND"
    )
    assert report.ticker == "FAKE4"
    assert report.status == STATUS_UNSUPPORTED
    assert report.capabilities[CAPABILITY_HISTORY] is False
    assert report.ttl_seconds == TTL_UNSUPPORTED
    assert report.error_code == "404_NOT_FOUND"

    # Agora is_supported deve retornar False para bloquear chamadas repetidas
    assert await service.is_supported("FAKE4", CAPABILITY_HISTORY) is False
    # Mas outra capacidade ainda nao testada permanece True (fail-open)
    assert await service.is_supported("FAKE4", CAPABILITY_QUOTE) is True


@pytest.mark.asyncio
async def test_partial_coverage_does_not_mark_asset_invalid(service: AssetCoverageService):
    # Ativo suporta historico, mas nao suporta proventos
    await service.record_capability("BDRX11", CAPABILITY_HISTORY, supported=True)
    report = await service.record_capability("BDRX11", CAPABILITY_DIVIDENDS, supported=False, error_code="404_NOT_FOUND")

    assert report.status == STATUS_PARTIAL
    assert report.capabilities[CAPABILITY_HISTORY] is True
    assert report.capabilities[CAPABILITY_DIVIDENDS] is False

    # Ativo continua operacional para historico, mas bloqueia proventos
    assert await service.is_supported("BDRX11", CAPABILITY_HISTORY) is True
    assert await service.is_supported("BDRX11", CAPABILITY_DIVIDENDS) is False


@pytest.mark.asyncio
async def test_transient_error_uses_shorter_ttl(service: AssetCoverageService):
    report = await service.record_capability(
        "ITUB4", CAPABILITY_HISTORY, supported=False, error_code="500_SERVER_ERROR"
    )
    assert report.ttl_seconds == TTL_TRANSIENT_ERROR


@pytest.mark.asyncio
async def test_list_and_clear_coverages(service: AssetCoverageService):
    await service.record_capability("BBAS3", CAPABILITY_HISTORY, supported=True)
    await service.record_capability("KNIP11", CAPABILITY_HISTORY, supported=True)

    reports = await service.list_all_coverages(limit=10)
    tickers = [r.ticker for r in reports]
    assert "BBAS3" in tickers
    assert "KNIP11" in tickers

    # Limpar BBAS3 individualmente
    await service.clear_coverage(ticker="BBAS3")
    assert await service.get_coverage("BBAS3") is None
    assert await service.get_coverage("KNIP11") is not None

    # Limpar geral
    await service.clear_coverage()
    reports_after = await service.list_all_coverages(limit=10)
    assert len(reports_after) == 0
