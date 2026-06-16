# Módulo de compatibilidade: re-exporta get_current_user de app.core.deps
# para manter compatibilidade com routers que importam de app.core.auth
from app.core.deps import get_current_user, oauth2_scheme  # noqa: F401

__all__ = ["get_current_user", "oauth2_scheme"]
