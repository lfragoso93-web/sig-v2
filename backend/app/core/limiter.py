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
from starlette.requests import Request

from app.core.config import settings


def get_client_ip(request: Request) -> str:
    """Resolve o IP real do cliente atras de Cloudflare Tunnel / Nginx."""
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip and cf_ip.strip():
        return cf_ip.strip()

    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        first_ip = forwarded_for.split(",")[0].strip()
        if first_ip:
            return first_ip

    real_ip = request.headers.get("X-Real-IP")
    if real_ip and real_ip.strip():
        return real_ip.strip()

    return get_remote_address(request)


_storage_uri = settings.REDIS_URL if settings.REDIS_URL else "memory://"

limiter = Limiter(
    key_func=get_client_ip,
    storage_uri=_storage_uri,
    default_limits=[],
)
