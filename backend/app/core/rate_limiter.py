"""
Rate limiters globais do processo.

BRAPI:
  brapi_limiter - token bucket asyncio para chamadas BRAPI.
  Configurado via BRAPI_RATE_LIMIT / BRAPI_RATE_BURST no .env.
  Defaults: 2 req/s, burst 5 (plano gratuito).
  Para plano Pro: BRAPI_RATE_LIMIT=10, BRAPI_RATE_BURST=20.

Alpha Vantage:
  alpha_vantage_limiter - token bucket asyncio para chamadas Alpha Vantage.
  Fixo em 4 req/min (conservador para o plano free: 25 req/min, 500 req/dia).
  Garante espaco para burst sem ultrapassar o limite diario.

Todos os limiters sao instanciados aqui para serem importados pelos servicos.
"""
import asyncio
import time

from app.core.config import settings


class TokenBucket:
    """
    Token bucket asyncio-safe para rate limiting.

    rate  - tokens adicionados por segundo (ex: 2.0 = 2 req/s)
    burst - capacidade maxima do bucket (pico instantaneo permitido)

    acquire() bloqueia ate um token estar disponivel.
    Criado lazy (_lock inicializado no primeiro acquire) para compatibilidade
    com o event loop do uvicorn.
    """

    def __init__(self, rate: float, burst: int):
        self.rate = rate
        self.burst = burst
        self._tokens: float = float(burst)
        self._last: float = time.monotonic()
        self._lock: asyncio.Lock | None = None

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def acquire(self) -> None:
        async with self._get_lock():
            while True:
                now = time.monotonic()
                elapsed = now - self._last
                self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
                self._last = now
                if self._tokens >= 1:
                    self._tokens -= 1
                    return
                wait = (1 - self._tokens) / self.rate
                await asyncio.sleep(wait)


# BRAPI - configurado via .env
brapi_limiter = TokenBucket(
    rate=settings.BRAPI_RATE_LIMIT,
    burst=settings.BRAPI_RATE_BURST,
)

# Alpha Vantage - 4 req/min fixo (conservador para plano free)
# 4/60 = ~0.067 tokens/segundo, burst 4
alpha_vantage_limiter = TokenBucket(
    rate=4 / 60,
    burst=4,
)
