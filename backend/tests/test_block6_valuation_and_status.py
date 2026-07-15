from datetime import date
from types import SimpleNamespace

from app.core.provider_status import (
    ProviderStatus,
    is_terminal_status,
    normalize_provider_status,
)
from app.models.asset import AssetType
from app.models.transaction import OperationType
from app.services.portfolio_snapshot_twr_service import build_open_quote_requirements


def _tx(ticker: str, asset_type: AssetType):
    return SimpleNamespace(
        ticker=ticker,
        asset_type=asset_type.value,
        date=date(2026, 1, 2),
        quantity=1,
        operation=OperationType.buy,
    )


def test_snapshot_quote_requirements_excludes_dedicated_and_no_quote_types():
    requirements = build_open_quote_requirements(
        [
            _tx("PETR4", AssetType.ACAO),
            _tx("TESOURO-SELIC-01032031", AssetType.TESOURO_DIRETO),
            _tx("PORQUINHO AUTOMATICO", AssetType.RENDA_FIXA),
        ],
        date(2026, 7, 15),
    )

    assert requirements == [("PETR4", AssetType.ACAO)]


def test_provider_status_normalizes_legacy_values_without_false_success():
    assert normalize_provider_status("NO_HISTORY") == ProviderStatus.HISTORY_UNAVAILABLE
    assert normalize_provider_status("NOT_FOUND") == ProviderStatus.SYMBOL_NOT_SUPPORTED
    assert normalize_provider_status("FAILED") == ProviderStatus.PROVIDER_ERROR
    assert normalize_provider_status("valor_desconhecido") == ProviderStatus.PROVIDER_ERROR


def test_terminal_provider_statuses_are_not_rescheduled_blindly():
    assert is_terminal_status("HISTORY_END_UNAVAILABLE") is True
    assert is_terminal_status("SYMBOL_NOT_SUPPORTED") is True
    assert is_terminal_status("OK") is False
    assert is_terminal_status(None) is False
