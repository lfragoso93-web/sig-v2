"""Servico de integracao com Google OAuth 2.0 (Issue #97).

Permite autenticacao federada via OpenID Connect, criacao automatica de conta
e vinculo seguro com contas preexistentes por e-mail verificado.
"""

import logging
import secrets
import urllib.parse
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.cache import get_redis
from app.core.config import settings

logger = logging.getLogger(__name__)

GOOGLE_AUTH_BASE = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
STATE_TTL_SECONDS = 600  # 10 minutos
_memory_oauth_states: set[str] = set()


async def create_oauth_state() -> str:
    """Gera e armazena um state aleatorio para prevencao de CSRF."""
    state = secrets.token_urlsafe(32)
    redis_client = await get_redis()
    if redis_client:
        try:
            await redis_client.set(
                f"oauth:state:{state}", "valid", ex=STATE_TTL_SECONDS
            )
            return state
        except Exception as exc:
            logger.warning("Erro ao salvar state OAuth no Redis: %s", exc)
    _memory_oauth_states.add(state)
    return state


async def verify_and_consume_oauth_state(state: str) -> bool:
    """Valida e consome o state de autenticacao OAuth contra CSRF."""
    if not state:
        return False
    redis_client = await get_redis()
    if redis_client:
        try:
            key = f"oauth:state:{state}"
            exists = await redis_client.get(key)
            if exists:
                await redis_client.delete(key)
                return True
            return False
        except Exception as exc:
            logger.warning("Erro ao validar state OAuth no Redis: %s", exc)
            return False

    if state in _memory_oauth_states:
        _memory_oauth_states.remove(state)
        return True
    return False


def get_google_auth_url(state: str) -> str:
    """Retorna o link de autorizacao Google OAuth 2.0."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth nao configurado no servidor.",
        )

    redirect_uri = (
        settings.GOOGLE_REDIRECT_URI
        or f"{settings.FRONTEND_URL}/auth/google/callback"
    )

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_BASE}?{urllib.parse.urlencode(params)}"


async def exchange_code_for_user_info(code: str) -> dict[str, Any]:
    """Troca o authorization code pelo perfil do usuario no Google."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth nao configurado no servidor.",
        )

    redirect_uri = (
        settings.GOOGLE_REDIRECT_URI
        or f"{settings.FRONTEND_URL}/auth/google/callback"
    )

    token_payload = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=15.0)) as client:
        token_resp = await client.post(GOOGLE_TOKEN_URL, data=token_payload)
        if token_resp.status_code != 200:
            logger.error(
                "Falha ao trocar code no Google OAuth: %d %s",
                token_resp.status_code,
                token_resp.text,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Falha na comunicacao com o Google. Codigo invalido.",
            )

        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token de acesso do Google ausente.",
            )

        headers = {"Authorization": f"Bearer {access_token}"}
        user_resp = await client.get(GOOGLE_USERINFO_URL, headers=headers)
        if user_resp.status_code != 200:
            logger.error(
                "Falha ao obter userinfo no Google: %d %s",
                user_resp.status_code,
                user_resp.text,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nao foi possivel obter informacoes do perfil Google.",
            )

        user_info = user_resp.json()
        return user_info
