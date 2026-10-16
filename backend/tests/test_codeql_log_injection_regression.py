from pathlib import Path


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

    assert "sanitize_log_value(exc)" in source
    assert "sanitize_log_value(symbol)" in source
