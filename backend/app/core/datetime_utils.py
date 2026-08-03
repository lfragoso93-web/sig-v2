"""Utilitários temporais compartilhados pelo backend."""

from datetime import UTC, datetime


def utc_now_naive() -> datetime:
    """Retorna o instante UTC atual sem tzinfo para colunas DateTime naive.

    Use apenas enquanto o contrato persistido da coluna for ``timezone=False``.
    Colunas timezone-aware devem receber ``datetime.now(UTC)`` diretamente.
    """

    return datetime.now(UTC).replace(tzinfo=None)
