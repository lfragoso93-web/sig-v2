# Módulo de compatibilidade: re-exporta get_current_user e o extrator de token
# para manter compatibilidade com routers que importam de app.core.auth
from app.core.deps import get_current_user, _bearer as oauth2_scheme  # noqa: F401

__all__ = ["get_current_user", "oauth2_scheme"]
