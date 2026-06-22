"""
Router de diagnostico - protegido por ADMIN_SECRET.

!!! ATENCAO: ENDPOINTS SENSIVEIS !!!
Este router permite redefinir senhas e criar usuarios com qualquer role.
Nao deve ser exposto em producao sem necessidade operacional ativa.

CICLO DE VIDA:
  Ativado: quando a env var ADMIN_SECRET esta definida (ver main.py).
  Desativar: remover ADMIN_SECRET do .env e fazer redeploy.
  Remover permanentemente: apagar este arquivo e o include_router em main.py.

SEGURANCA IMPLEMENTADA:
  - Autenticacao por header X-Admin-Secret (comparacao constante de tempo).
  - Rate limiting: DEBUG_RATE_LIMIT req/min por IP (default 5/minute) via slowapi.
  - Audit log estruturado: cada acesso registrado com timestamp, endpoint,
    IP, user-agent e resultado (sucesso/erro).
  - Todos os logs vao para o logger 'app.routers.debug' no nivel WARNING
    para aparecerem em qualquer configuracao de log de producao.

AUDIT LOG:
  Formato JSON para facilitar ingestao em ferramentas de observabilidade:
  {"event": "debug_access", "endpoint": "/debug/reset-password",
   "ip": "1.2.3.4", "user_agent": "...", "result": "success",
   "ts": "2026-06-22T19:00:00Z"}
"""
import hmac
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.models.user import User

router = APIRouter()
logger = logging.getLogger("app.routers.debug")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_limiter():
    """Importa limiter do main sem circular import."""
    from app.main import limiter
    return limiter


def _audit_log(
    request: Request,
    endpoint: str,
    result: str,
    detail: str = "",
) -> None:
    """
    Registra acesso ao router de debug no nivel WARNING.
    Formato estruturado para ingestao em ferramentas de observabilidade.
    """
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")[:120]  # trunca UA longo
    ts = datetime.now(timezone.utc).isoformat()
    logger.warning(
        '{"event": "debug_access", "endpoint": "%s", "ip": "%s", '
        '"user_agent": "%s", "result": "%s", "detail": "%s", "ts": "%s"}',
        endpoint, ip, ua, result, detail, ts,
    )


def check_secret(x_admin_secret: str = Header(...)) -> None:
    """
    Verifica ADMIN_SECRET usando comparacao em tempo constante (hmac.compare_digest)
    para prevenir timing attacks.
    """
    secret = os.getenv("ADMIN_SECRET", "")
    if not secret:
        raise HTTPException(status_code=503, detail="Endpoint de debug desabilitado")
    # hmac.compare_digest exige bytes ou str do mesmo tipo
    if not hmac.compare_digest(
        x_admin_secret.encode("utf-8"),
        secret.encode("utf-8"),
    ):
        raise HTTPException(status_code=403, detail="Acesso negado")


# ---------------------------------------------------------------------------
# GET /debug/users
# ---------------------------------------------------------------------------

@router.get("/users")
async def list_users(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_secret),
):
    """Lista todos os usuarios cadastrados. Audit log em cada chamada."""
    limiter = _get_limiter()
    await limiter.check(request, settings.DEBUG_RATE_LIMIT)

    result = await db.execute(
        select(User.id, User.name, User.email, User.role, User.is_active)
    )
    rows = result.all()
    _audit_log(request, "/debug/users", "success", f"{len(rows)} users returned")
    return [
        {
            "id": r.id,
            "name": r.name,
            "email": r.email,
            "role": str(r.role),
            "is_active": r.is_active,
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# POST /debug/reset-password
# ---------------------------------------------------------------------------

class ResetPasswordRequest(BaseModel):
    email: str
    new_password: str


@router.post("/reset-password")
async def reset_password(
    request: Request,
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_secret),
):
    """Redefine a senha de um usuario pelo email. Audit log em cada chamada."""
    limiter = _get_limiter()
    await limiter.check(request, settings.DEBUG_RATE_LIMIT)

    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user:
        _audit_log(request, "/debug/reset-password", "error", f"user not found: {data.email}")
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    new_hash = hash_password(data.new_password)
    user.hashed_password = new_hash
    user.is_active = True
    await db.commit()
    await db.refresh(user)

    ok = verify_password(data.new_password, user.hashed_password)
    _audit_log(request, "/debug/reset-password", "success", f"password reset for {user.email}")
    return {
        "message": f"Senha do usuario {user.email} redefinida com sucesso",
        "verify_ok": ok,
        "is_active": user.is_active,
    }


# ---------------------------------------------------------------------------
# POST /debug/create-user
# ---------------------------------------------------------------------------

class CreateUserRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str = "superadmin"


@router.post("/create-user")
async def create_user_debug(
    request: Request,
    data: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_secret),
):
    """Cria um usuario com qualquer role, ignorando restricoes de registro. Audit log."""
    limiter = _get_limiter()
    await limiter.check(request, settings.DEBUG_RATE_LIMIT)

    from app.models.user import UserRole

    result = await db.execute(select(User).where(User.email == data.email))
    existing = result.scalar_one_or_none()
    if existing:
        _audit_log(request, "/debug/create-user", "error", f"email already exists: {data.email}")
        raise HTTPException(status_code=409, detail="E-mail ja cadastrado")

    role = UserRole.superadmin if data.role == "superadmin" else UserRole.user
    user = User(
        name=data.name,
        email=data.email,
        hashed_password=hash_password(data.password),
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    _audit_log(request, "/debug/create-user", "success", f"user created: {user.email} role={role}")
    return {
        "message": f"Usuario {user.email} criado com sucesso",
        "id": user.id,
        "role": str(user.role),
    }
