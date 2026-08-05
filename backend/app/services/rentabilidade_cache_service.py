"""Invalidação canônica do cache legado de Rentabilidade.

Este módulo isola a responsabilidade residual de expirar as chaves
``rent:{portfolio_id}:*`` enquanto a Issue #151 remove o serviço legado.
"""

from __future__ import annotations

import logging

from app.core.cache import cache_delete

logger = logging.getLogger(__name__)

_RENTABILIDADE_CACHE_PREFIX = "rent"
_RENTABILIDADE_CACHE_SUFFIXES = ("kpis", "ativos", "classes")


def _rentabilidade_cache_key(portfolio_id: int, suffix: str) -> str:
    return f"{_RENTABILIDADE_CACHE_PREFIX}:{portfolio_id}:{suffix}"


async def invalidate_rentabilidade_cache(portfolio_id: int) -> None:
    """Expire todas as chaves conhecidas de Rentabilidade de uma carteira."""
    for suffix in _RENTABILIDADE_CACHE_SUFFIXES:
        try:
            await cache_delete(_rentabilidade_cache_key(portfolio_id, suffix))
        except Exception as exc:  # noqa: BLE001 - invalidation remains best effort
            logger.warning(
                "[rentabilidade-cache] falha ao invalidar cache %s/%s: %s",
                portfolio_id,
                suffix,
                exc,
            )
