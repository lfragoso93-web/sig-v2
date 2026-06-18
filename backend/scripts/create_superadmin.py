"""
Script de seed: cria ou atualiza o usuário superadmin.

Uso:
    cd backend
    python -m scripts.create_superadmin

Variáveis de ambiente opcionais (sobrescrevem os defaults abaixo):
    SUPERADMIN_EMAIL     default: admin@sig.local
    SUPERADMIN_PASSWORD  default: Admin@1234!
    SUPERADMIN_NAME      default: Super Admin

O script faz UPSERT:
  - Se o e-mail já existe -> atualiza senha, role=superadmin, is_active=True
  - Se não existe        -> cria usuário novo
"""
import asyncio
import os
import sys

# Garante que o import resolve a partir de backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.user import User, UserRole   # noqa: E402
from sqlalchemy import select                # noqa: E402

EMAIL    = os.getenv("SUPERADMIN_EMAIL",    "admin@sig.local")
PASSWORD = os.getenv("SUPERADMIN_PASSWORD", "Admin@1234!")
NAME     = os.getenv("SUPERADMIN_NAME",     "Super Admin")


async def main() -> None:
    print(f"\n➤  Configurando superadmin: {EMAIL}")

    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == EMAIL))
        user   = result.scalar_one_or_none()

        new_hash = hash_password(PASSWORD)

        if user:
            user.hashed_password = new_hash
            user.role            = UserRole.superadmin
            user.is_active       = True
            user.name            = NAME
            await db.commit()
            print(f"  ✅  Usuário atualizado   → role=superadmin, is_active=True")
        else:
            user = User(
                name=NAME,
                email=EMAIL,
                hashed_password=new_hash,
                role=UserRole.superadmin,
                is_active=True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            print(f"  ✅  Usuário criado       → id={user.id}")

    print(f"\n  E-mail : {EMAIL}")
    print(f"  Senha  : {PASSWORD}")
    print("\n  ⚠️  Troque a senha após o primeiro login!\n")


if __name__ == "__main__":
    asyncio.run(main())
