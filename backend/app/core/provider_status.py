"""Estados canonicos de sincronizacao de dados de mercado.

Os valores persistidos continuam strings para manter compatibilidade com a
migration atual, mas novos servicos devem importar estas constantes em vez de
espalhar literais pelo codigo.
"""
from __future__ import annotations

from enum import StrEnum


class ProviderStatus(StrEnum):
    PENDING = "PENDING"
    OK = "OK"
    HISTORY_START_EXHAUSTED = "HISTORY_START_EXHAUSTED"
    HISTORY_END_UNAVAILABLE = "HISTORY_END_UNAVAILABLE"
    HISTORY_UNAVAILABLE = "HISTORY_UNAVAILABLE"
    SYMBOL_NOT_SUPPORTED = "SYMBOL_NOT_SUPPORTED"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    INVALID_PRICE_DATA = "INVALID_PRICE_DATA"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    CANONICAL_ALIAS = "CANONICAL_ALIAS"


# Estados legados que podem existir em bancos anteriores. A normalizacao e
# somente semantica; a manutencao nao converte um erro desconhecido em sucesso.
LEGACY_STATUS_MAP: dict[str, ProviderStatus] = {
    "EMPTY": ProviderStatus.HISTORY_UNAVAILABLE,
    "NO_HISTORY": ProviderStatus.HISTORY_UNAVAILABLE,
    "MISSING": ProviderStatus.HISTORY_UNAVAILABLE,
    "NOT_FOUND": ProviderStatus.SYMBOL_NOT_SUPPORTED,
    "FAILED": ProviderStatus.PROVIDER_ERROR,
    "ERROR": ProviderStatus.PROVIDER_ERROR,
    "NONE": ProviderStatus.NOT_APPLICABLE,
}


def normalize_provider_status(value: object) -> ProviderStatus:
    raw = str(value or "").strip().upper()
    if not raw:
        return ProviderStatus.PENDING
    try:
        return ProviderStatus(raw)
    except ValueError:
        return LEGACY_STATUS_MAP.get(raw, ProviderStatus.PROVIDER_ERROR)


def is_terminal_status(value: object) -> bool:
    return normalize_provider_status(value) in {
        ProviderStatus.HISTORY_START_EXHAUSTED,
        ProviderStatus.HISTORY_END_UNAVAILABLE,
        ProviderStatus.HISTORY_UNAVAILABLE,
        ProviderStatus.SYMBOL_NOT_SUPPORTED,
        ProviderStatus.NOT_APPLICABLE,
        ProviderStatus.CANONICAL_ALIAS,
    }
