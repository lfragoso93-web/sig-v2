"""Testes para user_service — gerenciamento de usuarios."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_service import (
    get_user_by_email,
    get_user_by_id,
    create_user,
    update_user,
    list_users,
)
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate


@pytest.mark.asyncio
class TestGetUserByEmail:

    async def test_get_user_found(self):
        db = AsyncMock(spec=AsyncSession)
        
        user = MagicMock(spec=User)
        user.email = "user@example.com"
        user.name = "Test User"
        
        execute_result = AsyncMock()
        execute_result.scalar_one_or_none = AsyncMock(return_value=user)
        db.execute = AsyncMock(return_value=execute_result)
        
        result = await get_user_by_email(db, "user@example.com")
        
        assert result == user

    async def test_get_user_not_found(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = AsyncMock()
        execute_result.scalar_one_or_none = AsyncMock(return_value=None)
        db.execute = AsyncMock(return_value=execute_result)
        
        result = await get_user_by_email(db, "nonexistent@example.com")
        
        assert result is None


@pytest.mark.asyncio
class TestGetUserById:

    async def test_get_user_found(self):
        db = AsyncMock(spec=AsyncSession)
        
        user = MagicMock(spec=User)
        user.id = 1
        user.name = "Test User"
        
        execute_result = AsyncMock()
        execute_result.scalar_one_or_none = AsyncMock(return_value=user)
        db.execute = AsyncMock(return_value=execute_result)
        
        result = await get_user_by_id(db, 1)
        
        assert result == user

    async def test_get_user_not_found(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = AsyncMock()
        execute_result.scalar_one_or_none = AsyncMock(return_value=None)
        db.execute = AsyncMock(return_value=execute_result)
        
        result = await get_user_by_id(db, 999)
        
        assert result is None


@pytest.mark.asyncio
class TestCreateUser:

    async def test_create_user_success(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = AsyncMock()
        execute_result.scalar_one_or_none = AsyncMock(return_value=None)
        db.execute = AsyncMock(return_value=execute_result)
        
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        
        data = UserCreate(
            name="New User",
            email="new@example.com",
            password="password123",
        )
        
        with patch('app.services.user_service.hash_password', return_value="hashed_password"):
            user = await create_user(db, data)
        
        assert user is not None
        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

    async def test_create_user_duplicate_email(self):
        db = AsyncMock(spec=AsyncSession)
        
        existing_user = MagicMock(spec=User)
        
        execute_result = AsyncMock()
        execute_result.scalar_one_or_none = AsyncMock(return_value=existing_user)
        db.execute = AsyncMock(return_value=execute_result)
        
        data = UserCreate(
            name="Duplicate",
            email="existing@example.com",
            password="password123",
        )
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            await create_user(db, data)

    async def test_create_user_with_role(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = AsyncMock()
        execute_result.scalar_one_or_none = AsyncMock(return_value=None)
        db.execute = AsyncMock(return_value=execute_result)
        
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        
        data = UserCreate(
            name="Admin User",
            email="admin@example.com",
            password="password123",
        )
        
        with patch('app.services.user_service.hash_password', return_value="hashed_password"):
            user = await create_user(db, data, role=UserRole.admin)
        
        assert user is not None


@pytest.mark.asyncio
class TestUpdateUser:

    async def test_update_user_success(self):
        db = AsyncMock(spec=AsyncSession)
        
        existing_user = MagicMock(spec=User)
        existing_user.id = 1
        existing_user.name = "Old Name"
        existing_user.email = "old@example.com"
        
        get_result = AsyncMock()
        get_result.scalar_one_or_none = AsyncMock(return_value=existing_user)
        
        db.execute = AsyncMock(return_value=get_result)
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        
        data = UserUpdate(name="New Name")
        
        user = await update_user(db, 1, data)
        
        assert user == existing_user
        db.commit.assert_called_once()

    async def test_update_user_not_found(self):
        db = AsyncMock(spec=AsyncSession)
        
        get_result = AsyncMock()
        get_result.scalar_one_or_none = AsyncMock(return_value=None)
        db.execute = AsyncMock(return_value=get_result)
        
        data = UserUpdate(name="New Name")
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await update_user(db, 999, data)
        
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
class TestListUsers:

    async def test_list_users_empty(self):
        db = AsyncMock(spec=AsyncSession)
        
        count_result = AsyncMock()
        count_result.scalar_one = AsyncMock(return_value=0)
        
        list_result = AsyncMock()
        list_result.scalars = AsyncMock(return_value=list_result)
        list_result.all = AsyncMock(return_value=[])
        
        db.execute = AsyncMock(side_effect=[count_result, list_result])
        
        users, total = await list_users(db)
        
        assert users == []
        assert total == 0

    async def test_list_users_with_results(self):
        db = AsyncMock(spec=AsyncSession)
        
        user1 = MagicMock(spec=User)
        user1.id = 1
        user1.name = "User 1"
        
        user2 = MagicMock(spec=User)
        user2.id = 2
        user2.name = "User 2"
        
        count_result = AsyncMock()
        count_result.scalar_one = AsyncMock(return_value=2)
        
        list_result = AsyncMock()
        list_result.scalars = AsyncMock(return_value=list_result)
        list_result.all = AsyncMock(return_value=[user1, user2])
        
        db.execute = AsyncMock(side_effect=[count_result, list_result])
        
        users, total = await list_users(db)
        
        assert len(users) == 2
        assert total == 2

    async def test_list_users_pagination(self):
        db = AsyncMock(spec=AsyncSession)
        
        user = MagicMock(spec=User)
        
        count_result = AsyncMock()
        count_result.scalar_one = AsyncMock(return_value=50)
        
        list_result = AsyncMock()
        list_result.scalars = AsyncMock(return_value=list_result)
        list_result.all = AsyncMock(return_value=[user])
        
        db.execute = AsyncMock(side_effect=[count_result, list_result])
        
        users, total = await list_users(db, page=2, page_size=20)
        
        assert total == 50

    async def test_list_users_search(self):
        db = AsyncMock(spec=AsyncSession)
        
        user = MagicMock(spec=User)
        user.name = "John Doe"
        
        count_result = AsyncMock()
        count_result.scalar_one = AsyncMock(return_value=1)
        
        list_result = AsyncMock()
        list_result.scalars = AsyncMock(return_value=list_result)
        list_result.all = AsyncMock(return_value=[user])
        
        db.execute = AsyncMock(side_effect=[count_result, list_result])
        
        users, total = await list_users(db, search="John")
        
        assert len(users) == 1
