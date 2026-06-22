"""
Blacklist de refresh tokens em memoria com TTL automatico.

Design:
- Chave: jti (UUID unico por refresh token)
- Valor: timestamp de expiracao UTC (epoch float)
- Expurgo lazy: tokens vencidos sao removidos a cada insercao,
  evitando crescimento ilimitado sem precisar de task em background.
- Thread-safe via asyncio.Lock (mesmo loop do uvicorn).

Limitacao conhecida: a blacklist e perdida ao reiniciar o processo.
Isso e aceitavel para o estagio atual; em producao multi-instancia
substituir por Redis com SETEX.
"""
import asyncio
import time
from typing import Dict

_lock = asyncio.Lock()
_store: Dict[str, float] = {}  # jti -> exp (epoch UTC)


def _purge_expired() -> None:
    """Remove entradas ja vencidas. Chamar dentro do lock."""
    now = time.time()
    expired = [jti for jti, exp in _store.items() if exp <= now]
    for jti in expired:
        del _store[jti]


async def blacklist_token(jti: str, exp: float) -> None:
    """Adiciona jti a blacklist ate seu horario de expiracao."""
    async with _lock:
        _purge_expired()
        _store[jti] = exp


async def is_blacklisted(jti: str) -> bool:
    """Retorna True se o jti estiver na blacklist e ainda nao tiver vencido."""
    async with _lock:
        exp = _store.get(jti)
        if exp is None:
            return False
        if time.time() > exp:
            del _store[jti]
            return False
        return True


async def blacklist_size() -> int:
    """Retorna tamanho atual da blacklist (util para debug/monitoramento)."""
    async with _lock:
        _purge_expired()
        return len(_store)
