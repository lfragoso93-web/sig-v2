"""
Instancia global do rate limiter (slowapi).

Centralizado aqui para evitar importacao circular entre
app.main (que inclui os routers) e os routers que precisam
do limiter antes de app.main terminar de inicializar.

Uso nos routers:
    from app.core.limiter import limiter
    @limiter.limit("10/minute")
    async def meu_endpoint(request: Request, ...): ...

O limiter tambem e injetado em app.state.limiter em main.py
para que o SlowAPIMiddleware funcione corretamente.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

_storage_uri = settings.REDIS_URL if settings.REDIS_URL else "memory://"

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_storage_uri,
    default_limits=[],
)
