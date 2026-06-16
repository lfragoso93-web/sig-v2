"""Script de seed: cria o usuário superadmin padrão se não existir.

Uso:
    cd backend
    python seed_admin.py

Variáveis de ambiente necessárias (ou defina no .env):
    DATABASE_URL  — URL síncrona do PostgreSQL
    ADMIN_EMAIL   — (opcional) default: admin@agi.com
    ADMIN_PASSWORD — (opcional) default: Admin@1234
    ADMIN_NAME     — (opcional) default: Administrador
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

ADMIN_EMAIL    = os.getenv("ADMIN_EMAIL",    "admin@agi.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@1234")
ADMIN_NAME     = os.getenv("ADMIN_NAME",     "Administrador")


async def seed():
    # Importações aqui para garantir que o env já foi carregado
    from app.core.database import AsyncSessionLocal
    from app.models.user import User, UserRole
    from app.services.user_service import get_user_by_email
    from app.core.security import hash_password
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        existing = await get_user_by_email(db, ADMIN_EMAIL)
        if existing:
            print(f"[seed] Usuário {ADMIN_EMAIL} já existe (id={existing.id}, role={existing.role}).")
            # Garante que seja superadmin
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
        print(f"[seed] Senha inicial: {ADMIN_PASSWORD}  ← troque após o primeiro login!")


if __name__ == "__main__":
    asyncio.run(seed())
