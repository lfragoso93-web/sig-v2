"""
Rate limiter baseado em token bucket (in-memory, asyncio-safe).

Nao depende de Redis — funciona em qualquer ambiente.
Para producao com multiplos workers/processos, substituir por
implementacao Redis (ex: redis-py-limiter ou limits).

Uso:
    from app.core.rate_limiter import brapi_limiter

    async def minha_funcao():
        await brapi_limiter.acquire()  # bloqueia ate ter token disponivel
        resultado = await chamar_brapi()
"""
import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class TokenBucketLimiter:
    """
    Token bucket simples.

    - rate:  tokens adicionados por segundo.
    - burst: capacidade maxima do bucket (pico permitido).

    Cada chamada a acquire() consome 1 token. Se o bucket estiver
    vazio, aguarda assincronamente ate o proximo token ser gerado.
    """

    def __init__(self, rate: float, burst: int) -> None:
        self._rate = rate          # tokens/segundo
        self._burst = burst        # capacidade maxima
        self._tokens = float(burst)  # comeca cheio
        self._last = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last
        self._tokens = min(self._burst, self._tokens + elapsed * self._rate)
        self._last = now

    async def acquire(self, tokens: int = 1) -> None:
        async with self._lock:
            while True:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return
                # Calcula quanto tempo esperar ate ter tokens suficientes
                wait = (tokens - self._tokens) / self._rate
                logger.debug(
                    "[rate_limiter] bucket vazio — aguardando %.2fs", wait
                )
                await asyncio.sleep(wait)

    def available(self) -> float:
        """Retorna tokens disponiveis no momento (sem lock — apenas informativo)."""
        elapsed = time.monotonic() - self._last
        return min(self._burst, self._tokens + elapsed * self._rate)


def _build_brapi_limiter() -> TokenBucketLimiter:
    """Constroi o limiter com settings; importado lazily para evitar circular import."""
    from app.core.config import settings
    return TokenBucketLimiter(
        rate=settings.BRAPI_RATE_LIMIT,
        burst=settings.BRAPI_RATE_BURST,
    )


# Singleton — criado na primeira importacao do modulo
brapi_limiter: TokenBucketLimiter = _build_brapi_limiter()
