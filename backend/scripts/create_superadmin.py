"""
Script de seed: cria ou atualiza o usuário superadmin.
Rodado automaticamente pelo entrypoint.sh a cada deploy.

Variáveis de ambiente (definidas no .env / Render env vars):
    SUPERADMIN_EMAIL     default: admin@sig.local
    SUPERADMIN_PASSWORD  default: Admin@1234!
    SUPERADMIN_NAME      default: Super Admin

Faz UPSERT:
  - Se o e-mail já existe -> atualiza senha, role=superadmin, is_active=True
  - Se não existe         -> cria usuário novo
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings        # noqa: E402
from app.core.database import async_session # noqa: E402
from app.core.security import hash_password # noqa: E402
from app.models.user import User, UserRole  # noqa: E402
from sqlalchemy import select               # noqa: E402


async def main() -> None:
    email    = settings.SUPERADMIN_EMAIL
    password = settings.SUPERADMIN_PASSWORD
    name     = settings.SUPERADMIN_NAME

    print(f"[seed] Configurando superadmin: {email}")

    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == email))
        user   = result.scalar_one_or_none()
        new_hash = hash_password(password)

        if user:
            user.hashed_password = new_hash
            user.role            = UserRole.superadmin
            user.is_active       = True
            user.name            = name
            await db.commit()
            print(f"[seed] Superadmin atualizado (id={user.id})")
        else:
            user = User(
                name=name,
                email=email,
                hashed_password=new_hash,
                role=UserRole.superadmin,
                is_active=True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            print(f"[seed] Superadmin criado (id={user.id})")

    print(f"[seed] OK — login: {email}")


if __name__ == "__main__":
    asyncio.run(main())
