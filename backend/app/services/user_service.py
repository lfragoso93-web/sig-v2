from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from fastapi import HTTPException, status
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate, UserAdminUpdate
from app.core.security import hash_password
from app.models.system_config import SystemConfig
from typing import Optional


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def is_registration_allowed(db: AsyncSession) -> bool:
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.key == "allow_registration")
    )
    config = result.scalar_one_or_none()
    return config is None or config.value.lower() == "true"


async def count_users(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(User))
    return result.scalar_one()


async def create_user(
    db: AsyncSession,
    data: UserCreate,
    role: UserRole = UserRole.user,
) -> User:
    existing = await get_user_by_email(db, data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail já cadastrado",
        )
    user = User(
        name=data.name,
        email=data.email,
        hashed_password=hash_password(data.password),
        role=role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def update_user_profile(db: AsyncSession, user: User, data: UserUpdate) -> User:
    if data.name is not None:
        user.name = data.name
    if data.avatar_url is not None:
        user.avatar_url = data.avatar_url
    await db.flush()
    await db.refresh(user)
    return user


async def admin_update_user(db: AsyncSession, user_id: int, data: UserAdminUpdate) -> User:
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if data.name is not None:
        user.name = data.name
    if data.email is not None:
        existing = await get_user_by_email(db, data.email)
        if existing and existing.id != user_id:
            raise HTTPException(status_code=409, detail="E-mail já em uso")
        user.email = data.email
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    await db.flush()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user_id: int) -> None:
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    await db.delete(user)


async def list_users(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
) -> tuple[list[User], int]:
    query = select(User)
    count_query = select(func.count()).select_from(User)
    if search:
        like = f"%{search}%"
        query = query.where((User.name.ilike(like)) | (User.email.ilike(like)))
        count_query = count_query.where((User.name.ilike(like)) | (User.email.ilike(like)))
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    query = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all(), total
