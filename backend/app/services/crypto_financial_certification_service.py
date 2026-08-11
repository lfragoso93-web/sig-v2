"""Política DB-first para certificação financeira de CRIPTO.

Este módulo não descobre o universo candidato e não chama providers. Ele apenas
classifica o lifecycle persistido de um ativo CRIPTO candidato. A política é
intencionalmente fail-closed: somente estados explicitamente aprovados podem
participar de fluxos financeiros certificados.
"""
from __future__ import annotations

FINANCIALLY_CERTIFIED_CRYPTO_STATUSES = frozenset(
    {
        "HISTORY_START_EXHAUSTED",
        "HISTORY_START_SHALLOW_VERIFIED",
    }
)


def is_crypto_financially_certified(provider_status: str | None) -> bool:
    """Retorna True somente para lifecycle CRIPTO explicitamente certificado."""
    normalized = str(provider_status or "").strip().upper()
    return normalized in FINANCIALLY_CERTIFIED_CRYPTO_STATUSES
