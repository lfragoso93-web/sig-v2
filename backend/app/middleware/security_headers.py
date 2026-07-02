"""
Middleware para adicionar headers de segurança HTTP
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adiciona headers de segurança recomendados:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security: max-age=31536000; includeSubDomains
    - Content-Security-Policy: política restritiva
    - Referrer-Policy: strict-origin-when-cross-origin
    """

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        
        # Previne MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Previne clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS Protection (ainda útil para navegadores antigos)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # HSTS - força HTTPS (apenas em produção)
        if not request.url.hostname in ["localhost", "127.0.0.1"]:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        
        # Content Security Policy - política restritiva
        # Ajuste conforme necessário baseado nos recursos externos usados
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        
        # Referrer Policy - controla informações de referrer
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy - desabilita features não utilizadas
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=()"
        )
        
        return response
