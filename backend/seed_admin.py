"""Seed idempotente do usuário superadmin inicial."""

import asyncio
import os

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole

ADMIN_NAME = os.getenv("ADMIN_NAME", "Administrador")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@sgi.local")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")


async def seed() -> None:
    if not ADMIN_PASSWORD:
        raise RuntimeError("ADMIN_PASSWORD must be configured before seeding the superadmin")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == ADMIN_EMAIL))
        existing = result.scalar_one_or_none()
        if existing:
            print(f"[seed] Usuário {ADMIN_EMAIL} já existe (id={existing.id}, role={existing.role}).")
            if existing.role != UserRole.superadmin:
                existing.role = UserRole.superadmin
                await db.commit()
                print("[seed] Role atualizado para superadmin.")
            return

        user = User(
            name=ADMIN_NAME,
            email=ADMIN_EMAIL,
            hashed_password=hash_password(ADMIN_PASSWORD),
            role=UserRole.superadmin,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        print(f"[seed] Superadmin criado: {ADMIN_EMAIL} (id={user.id})")
        print("[seed] Senha inicial configurada por variável de ambiente; altere-a após o primeiro login.")


if __name__ == "__main__":
    asyncio.run(seed())
