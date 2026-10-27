from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import treasury_catalog_service as treasury_catalog

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_codeql_treasury_catalog_logs_sanitize_external_values() -> None:
    source = (
        BACKEND_ROOT / "app/services/treasury_catalog_service.py"
    ).read_text(encoding="utf-8")

    assert "from app.core.log_safety import sanitize_log_value" in source
    assert "sanitize_log_value(value)" in source
    assert "sanitize_log_value(resolved)" in source
    assert 'logger.info("[treasury_catalog]' not in source
    assert 'logger.warning("[treasury_catalog]' not in source


def test_codeql_portfolio_fallback_logs_sanitize_context_and_reason() -> None:
    source = (BACKEND_ROOT / "app/services/portfolio_service.py").read_text(
        encoding="utf-8"
    )

    assert "from app.core.log_safety import sanitize_log_value" in source
    assert source.count("sanitize_log_value(portfolio_id)") >= 2
    assert source.count("sanitize_log_value(exc)") >= 2



def test_codeql_fixed_income_fallback_logs_sanitize_external_values() -> None:
    source = (
        BACKEND_ROOT / "app/services/fixed_income_valuation_service.py"
    ).read_text(encoding="utf-8")

    assert "from app.core.log_safety import sanitize_log_value" in source
    assert source.count("sanitize_log_value(key)") >= 2
    assert "sanitize_log_value(exc)" in source


def test_codeql_treasury_seed_logs_sanitize_external_values() -> None:
    source = (
        BACKEND_ROOT / "app/services/treasury_catalog_service.py"
    ).read_text(encoding="utf-8")

    assert source.count("sanitize_log_value(exc)") >= 2
    assert "sanitize_log_value(symbol)" in source


@pytest.mark.asyncio
async def test_codeql_treasury_catalog_no_match_log_escapes_newlines(
    caplog: pytest.LogCaptureFixture,
) -> None:
    db = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.first.return_value = None
    db.execute.return_value = execute_result
    raw = "titulo inexistente\nINJECTED"

    with patch.object(
        treasury_catalog, "canonical_treasury_symbol_from_text", return_value=None
    ), patch.object(treasury_catalog, "_treasury_assets", new=AsyncMock(return_value=[])):
        result = await treasury_catalog.resolve_treasury_symbol(db, raw)

    assert result is None
    assert "[treasury_catalog] sem match" in caplog.text
    assert "titulo inexistente\\\\nINJECTED" in caplog.text
    assert "titulo inexistente\nINJECTED" not in caplog.text


@pytest.mark.asyncio
async def test_codeql_treasury_catalog_resolution_log_escapes_newlines(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("INFO")
    db = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.first.return_value = None
    db.execute.return_value = execute_result
    raw = "descricao tesouro ipca\n2035 desconhecida"
    asset = SimpleNamespace(ticker="tesouro-ipca-2035", name="Tesouro IPCA 2035")

    with patch.object(
        treasury_catalog, "canonical_treasury_symbol_from_text", return_value=None
    ), patch.object(
        treasury_catalog, "_treasury_assets", new=AsyncMock(return_value=[asset])
    ):
        result = await treasury_catalog.resolve_treasury_symbol(db, raw)

    assert result == "tesouro-ipca-2035"
    assert "[treasury_catalog]" in caplog.text
    assert "descricao tesouro ipca\\\\n2035 desconhecida" in caplog.text
    assert "descricao tesouro ipca\n2035 desconhecida" not in caplog.text


@pytest.mark.asyncio
async def test_codeql_treasury_seed_fetch_error_log_escapes_newlines(
    caplog: pytest.LogCaptureFixture,
) -> None:
    db = AsyncMock()
    malicious_error = RuntimeError("provider failed\nINJECTED")

    with patch.object(
        treasury_catalog,
        "fetch_treasury_catalog",
        new=AsyncMock(side_effect=malicious_error),
    ):
        result = await treasury_catalog.seed_treasury_assets(db)

    assert result.errors == 1
    assert "provider failed\\nINJECTED" in caplog.text
    assert "provider failed\nINJECTED" not in caplog.text


@pytest.mark.asyncio
async def test_codeql_treasury_seed_item_error_log_escapes_symbol_and_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    db = AsyncMock()
    db.execute.side_effect = RuntimeError("save failed\nINJECTED")
    item = {"symbol": "bond\nINJECTED"}
    consolidation = SimpleNamespace(consolidated=0, errors=0)

    with patch.object(
        treasury_catalog, "fetch_treasury_catalog", new=AsyncMock(return_value=[item])
    ), patch.object(
        treasury_catalog,
        "consolidate_legacy_educa_identities",
        new=AsyncMock(return_value=consolidation),
    ):
        result = await treasury_catalog.seed_treasury_assets(db, commit=False)

    assert result.errors == 1
    assert "erro ao salvar" in caplog.text
    assert "bond\\ninjected" in caplog.text
    assert "save failed\\nINJECTED" in caplog.text
    assert "bond\ninjected" not in caplog.text
    assert "save failed\nINJECTED" not in caplog.text


def test_codeql_asset_provider_verification_logs_sanitize_external_values() -> None:
    source = (
        BACKEND_ROOT / "app/services/asset_provider_verification_service.py"
    ).read_text(encoding="utf-8")

    assert "from app.core.log_safety import sanitize_log_value" in source
    assert source.count("sanitize_log_value(normalized_ticker)") >= 4
    assert source.count("sanitize_log_value(resolved_ticker)") >= 2
    assert source.count("sanitize_log_value(exc)") >= 6


def test_codeql_brapi_logs_sanitize_external_values() -> None:
    source = (
        BACKEND_ROOT / "app/integrations/brapi.py"
    ).read_text(encoding="utf-8")

    assert "from app.core.log_safety import sanitize_log_value" in source
    assert "sanitize_log_value(ticker)" in source
    assert "sanitize_log_value(e)" in source
