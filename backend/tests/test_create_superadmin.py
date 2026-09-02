import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from scripts import create_superadmin as seed


class _FixtureSession:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, *_args):
        return False


def _configure_seed(monkeypatch, db: AsyncSession) -> None:
    monkeypatch.setattr(seed, "AsyncSessionLocal", lambda: _FixtureSession(db))
    monkeypatch.setattr(seed.settings, "SUPERADMIN_EMAIL", "admin@sgi.com")
    monkeypatch.setattr(seed.settings, "SUPERADMIN_PASSWORD", "Admin@1234!")
    monkeypatch.setattr(seed.settings, "SUPERADMIN_NAME", "Super Admin")


async def _users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).order_by(User.id))
    return list(result.scalars().all())


@pytest.mark.asyncio
async def test_creates_canonical_superadmin(
    db: AsyncSession,
    monkeypatch,
) -> None:
    _configure_seed(monkeypatch, db)

    await seed.main()

    users = await _users(db)

    assert len(users) == 1
    assert users[0].email == "admin@sgi.com"
    assert users[0].role == UserRole.superadmin
    assert users[0].is_active is True
    assert users[0].name == "Super Admin"


@pytest.mark.asyncio
async def test_updates_existing_canonical_superadmin_idempotently(
    db: AsyncSession,
    monkeypatch,
) -> None:
    existing = User(
        name="Old Name",
        email="admin@sgi.com",
        hashed_password="old-hash",
        role=UserRole.user,
        is_active=False,
    )
    db.add(existing)
    await db.commit()
    await db.refresh(existing)
    existing_id = existing.id

    _configure_seed(monkeypatch, db)

    await seed.main()
    await seed.main()

    users = await _users(db)

    assert len(users) == 1
    assert users[0].id == existing_id
    assert users[0].email == "admin@sgi.com"
    assert users[0].role == UserRole.superadmin
    assert users[0].is_active is True
    assert users[0].name == "Super Admin"


@pytest.mark.asyncio
async def test_legacy_superadmin_is_not_modified(
    db: AsyncSession,
    monkeypatch,
) -> None:
    legacy = User(
        name="Legacy Admin",
        email="admin@sig.local",
        hashed_password="legacy-hash",
        role=UserRole.superadmin,
        is_active=True,
    )
    db.add(legacy)
    await db.commit()
    await db.refresh(legacy)

    legacy_id = legacy.id
    legacy_hash = legacy.hashed_password

    _configure_seed(monkeypatch, db)

    await seed.main()

    users = await _users(db)
    by_email = {user.email: user for user in users}

    assert len(users) == 2

    assert by_email["admin@sig.local"].id == legacy_id
    assert by_email["admin@sig.local"].hashed_password == legacy_hash
    assert by_email["admin@sig.local"].name == "Legacy Admin"
    assert by_email["admin@sig.local"].role == UserRole.superadmin
    assert by_email["admin@sig.local"].is_active is True

    assert by_email["admin@sgi.com"].role == UserRole.superadmin
    assert by_email["admin@sgi.com"].is_active is True


@pytest.mark.asyncio
async def test_existing_canonical_and_legacy_can_coexist(
    db: AsyncSession,
    monkeypatch,
) -> None:
    canonical = User(
        name="Admin",
        email="admin@sgi.com",
        hashed_password="canonical-old-hash",
        role=UserRole.user,
        is_active=False,
    )
    legacy = User(
        name="Legacy Admin",
        email="admin@sig.local",
        hashed_password="legacy-hash",
        role=UserRole.superadmin,
        is_active=True,
    )
    db.add_all([canonical, legacy])
    await db.commit()
    await db.refresh(canonical)
    await db.refresh(legacy)

    canonical_id = canonical.id
    legacy_id = legacy.id
    legacy_hash = legacy.hashed_password

    _configure_seed(monkeypatch, db)

    await seed.main()

    users = await _users(db)
    by_email = {user.email: user for user in users}

    assert len(users) == 2

    assert by_email["admin@sgi.com"].id == canonical_id
    assert by_email["admin@sgi.com"].role == UserRole.superadmin
    assert by_email["admin@sgi.com"].is_active is True
    assert by_email["admin@sgi.com"].name == "Super Admin"

    assert by_email["admin@sig.local"].id == legacy_id
    assert by_email["admin@sig.local"].hashed_password == legacy_hash
    assert by_email["admin@sig.local"].role == UserRole.superadmin
    assert by_email["admin@sig.local"].is_active is True
