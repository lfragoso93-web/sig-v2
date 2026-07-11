from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from app.models.user import User, UserRole
from app.schemas.user import UserUpdate, UserCreate, UserAdminUpdate
from app.core.security import hash_password


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def update_user(db: AsyncSession, user_id: int, data: UserUpdate) -> User:
    user = await get_user_by_id(db, user_id)
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user


async def create_user(
    db: AsyncSession,
    data: UserCreate,
    role: UserRole = UserRole.user,
) -> User:
    from fastapi import HTTPException
    existing = await get_user_by_email(db, data.email)
    if existing:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
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
    return user


async def list_users(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
) -> tuple[list[User], int]:
    query = select(User)
    count_query = select(func.count()).select_from(User)

    if search:
        like = f"%{search}%"
        from sqlalchemy import or_
        query = query.where(or_(User.name.ilike(like), User.email.ilike(like)))
        count_query = count_query.where(or_(User.name.ilike(like), User.email.ilike(like)))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(User.id).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    users = list(result.scalars().all())
    return users, total


async def admin_update_user(
    db: AsyncSession,
    user_id: int,
    data: UserAdminUpdate,
) -> User:
    from fastapi import HTTPException
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    removes_active_superadmin = (
        user.role == UserRole.superadmin
        and user.is_active
        and (
            (data.role is not None and data.role != UserRole.superadmin)
            or data.is_active is False
        )
    )
    if removes_active_superadmin and await count_active_superadmins(db) <= 1:
        raise HTTPException(status_code=400, detail="Nao e possivel remover o ultimo SuperAdmin ativo")
    if data.email and data.email != user.email:
        existing = await get_user_by_email(db, data.email)
        if existing and existing.id != user_id:
            raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user_id: int) -> None:
    """
    Remove o usuario e todos os dados associados.

    Usa DELETE SQL direto com synchronize_session=False para deixar o
    PostgreSQL executar ON DELETE CASCADE nativamente em todas as tabelas
    filhas (portfolios, irpf_records, irpf_losses, etc.).

    O ORM delete (db.delete(obj)) nao funciona corretamente com AsyncSession
    porque nao faz eager load automatico dos relacionamentos, causando
    violacao de FK constraint.
    """
    from fastapi import HTTPException

    # Confirma existencia antes de deletar
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if user.role == UserRole.superadmin and user.is_active and await count_active_superadmins(db) <= 1:
        raise HTTPException(status_code=400, detail="Nao e possivel remover o ultimo SuperAdmin ativo")

    # DELETE SQL direto — PostgreSQL executa ON DELETE CASCADE nas FKs
    stmt = delete(User).where(User.id == user_id)
    await db.execute(stmt)
    await db.commit()


async def count_active_superadmins(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count()).select_from(User).where(
            User.role == UserRole.superadmin,
            User.is_active.is_(True),
        )
    )
    return result.scalar_one()


async def count_users(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(User))
    return result.scalar_one()
