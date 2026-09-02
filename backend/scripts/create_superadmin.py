"""
Script de seed do superadmin canônico.
Executado automaticamente pelo entrypoint.sh a cada deploy.

Variáveis de ambiente:
    SUPERADMIN_EMAIL     default: admin@sgi.com
    SUPERADMIN_PASSWORD  default: Admin@1234!
    SUPERADMIN_NAME      default: Super Admin

Comportamento:
  - Se o e-mail configurado já existe, atualiza senha, role e estado.
  - Se não existe, cria o superadmin configurado.
  - Não renomeia, remove nem modifica outros superadmins.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import AsyncSessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402


async def main() -> None:
    email = settings.SUPERADMIN_EMAIL
    password = settings.SUPERADMIN_PASSWORD
    name = settings.SUPERADMIN_NAME

    print(f"[seed] Configurando superadmin: {email}")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        new_hash = hash_password(password)

        if user is not None:
            user.hashed_password = new_hash
            user.role = UserRole.superadmin
            user.is_active = True
            user.name = name

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

    print(f"[seed] OK - login: {email}")


if __name__ == "__main__":
    asyncio.run(main())
