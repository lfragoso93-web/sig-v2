"""Invalidação dos caches ainda usados pelo resultado por ativo."""
from app.core.cache import cache_delete


async def flush_rentabilidade_cache(portfolio_id: int) -> None:
    """Remove apenas caches legados ainda relacionados ao resultado por ativo."""
    for suffix in ("ativos", "classes", "kpis"):
        try:
            await cache_delete(f"rent:{portfolio_id}:{suffix}")
        except Exception:
            # Cache é auxiliar e nunca deve bloquear gravações da carteira.
            pass
