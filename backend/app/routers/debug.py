"""
Router de diagnostico TEMPORARIO.
Protegido pela env var ADMIN_SECRET.
Remova este arquivo quando nao precisar mais.
"""
import os
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import User
from app.core.security import hash_password, verify_password
from pydantic import BaseModel

router = APIRouter()


def check_secret(x_admin_secret: str = Header(...)):
    secret = os.getenv("ADMIN_SECRET", "")
    if not secret or x_admin_secret != secret:
        raise HTTPException(status_code=403, detail="Acesso negado")


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_secret),
):
    """Lista todos os usuarios cadastrados."""
    result = await db.execute(select(User.id, User.name, User.email, User.role, User.is_active))
    rows = result.all()
    return [{"id": r.id, "name": r.name, "email": r.email, "role": str(r.role), "is_active": r.is_active} for r in rows]


class ResetPasswordRequest(BaseModel):
    email: str
    new_password: str


@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_secret),
):
    """Redefine a senha de um usuario pelo email."""
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    new_hash = hash_password(data.new_password)
    user.hashed_password = new_hash
    user.is_active = True

    await db.commit()
    await db.refresh(user)

    # Verifica se o hash foi salvo corretamente
    ok = verify_password(data.new_password, user.hashed_password)
    return {
        "message": f"Senha do usuario {user.email} redefinida com sucesso",
        "verify_ok": ok,
        "is_active": user.is_active,
    }


class CreateUserRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str = "superadmin"


@router.post("/create-user")
async def create_user_debug(
    data: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_secret),
):
    """Cria um usuario com qualquer role, ignorando restricoes de registro."""
    from app.models.user import UserRole
    result = await db.execute(select(User).where(User.email == data.email))
    existing = result.scalar_one_or_none()
    if existing:
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
    return {"message": f"Usuario {user.email} criado com sucesso", "id": user.id, "role": str(user.role)}
