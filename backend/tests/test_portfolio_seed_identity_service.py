from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.certification import portfolio_seed_identity_service as sut
from app.certification.portfolio_seed_contract import (
    SYNTHETIC_OWNERSHIP_MARKER,
    SYNTHETIC_PORTFOLIO_NAME,
    SYNTHETIC_USER_EMAIL,
    SYNTHETIC_USER_NAME,
)
from app.models.user import UserRole


PASSWORD = "CertSeed#303Pass"


def _user(**overrides):
    values = {
        "id": 303,
        "email": SYNTHETIC_USER_EMAIL,
        "name": SYNTHETIC_USER_NAME,
        "role": UserRole.user,
        "is_active": True,
        "hashed_password": "synthetic-hash",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _portfolio(**overrides):
    values = {
        "id": 404,
        "user_id": 303,
        "name": SYNTHETIC_PORTFOLIO_NAME,
        "description": SYNTHETIC_OWNERSHIP_MARKER,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.asyncio
async def test_provisions_new_user_and_portfolio_through_canonical_services(monkeypatch):
    db = SimpleNamespace()
    created_user = _user()
    created_portfolio = _portfolio()

    monkeypatch.setattr(
        sut.user_service,
        "get_user_by_email",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(sut, "_load_reserved_portfolios", AsyncMock(return_value=[]))
    create_user = AsyncMock(return_value=created_user)
    create_portfolio = AsyncMock(return_value=created_portfolio)
    monkeypatch.setattr(sut.user_service, "create_user", create_user)
    monkeypatch.setattr(sut.portfolio_service, "create_portfolio", create_portfolio)

    result = await sut.provision_synthetic_user_portfolio(db, password=PASSWORD)

    assert result == sut.SyntheticSeedProvisionResult(
        user_id=303,
        portfolio_id=404,
        user_created=True,
        portfolio_created=True,
    )
    user_data = create_user.await_args.args[1]
    assert user_data.email == SYNTHETIC_USER_EMAIL
    assert user_data.name == SYNTHETIC_USER_NAME
    assert user_data.password == PASSWORD
    assert create_user.await_args.kwargs["role"] == UserRole.user
    portfolio_data = create_portfolio.await_args.args[2]
    assert portfolio_data.name == SYNTHETIC_PORTFOLIO_NAME
    assert portfolio_data.description == SYNTHETIC_OWNERSHIP_MARKER


@pytest.mark.asyncio
async def test_replay_reuses_exact_owned_identity_without_writes(monkeypatch):
    db = SimpleNamespace()
    existing_user = _user()
    existing_portfolio = _portfolio()

    monkeypatch.setattr(
        sut.user_service,
        "get_user_by_email",
        AsyncMock(return_value=existing_user),
    )
    monkeypatch.setattr(
        sut,
        "_load_reserved_portfolios",
        AsyncMock(return_value=[existing_portfolio]),
    )
    monkeypatch.setattr(
        sut.portfolio_service,
        "list_portfolios",
        AsyncMock(return_value=[existing_portfolio]),
    )
    monkeypatch.setattr(sut, "verify_password", lambda plain, hashed: True)
    create_user = AsyncMock()
    create_portfolio = AsyncMock()
    monkeypatch.setattr(sut.user_service, "create_user", create_user)
    monkeypatch.setattr(sut.portfolio_service, "create_portfolio", create_portfolio)

    result = await sut.provision_synthetic_user_portfolio(db, password=PASSWORD)

    assert result.user_created is False
    assert result.portfolio_created is False
    create_user.assert_not_awaited()
    create_portfolio.assert_not_awaited()


@pytest.mark.asyncio
async def test_existing_owned_user_without_portfolio_creates_only_portfolio(monkeypatch):
    db = SimpleNamespace()
    existing_user = _user()
    created_portfolio = _portfolio()

    monkeypatch.setattr(
        sut.user_service,
        "get_user_by_email",
        AsyncMock(return_value=existing_user),
    )
    monkeypatch.setattr(sut, "_load_reserved_portfolios", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        sut.portfolio_service,
        "list_portfolios",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(sut, "verify_password", lambda plain, hashed: True)
    create_user = AsyncMock()
    create_portfolio = AsyncMock(return_value=created_portfolio)
    monkeypatch.setattr(sut.user_service, "create_user", create_user)
    monkeypatch.setattr(sut.portfolio_service, "create_portfolio", create_portfolio)

    result = await sut.provision_synthetic_user_portfolio(db, password=PASSWORD)

    assert result.user_created is False
    assert result.portfolio_created is True
    create_user.assert_not_awaited()
    create_portfolio.assert_awaited_once()


@pytest.mark.asyncio
async def test_refuses_reserved_email_with_different_user_name(monkeypatch):
    db = SimpleNamespace()
    monkeypatch.setattr(
        sut.user_service,
        "get_user_by_email",
        AsyncMock(return_value=_user(name="Different User")),
    )
    monkeypatch.setattr(sut, "_load_reserved_portfolios", AsyncMock(return_value=[]))

    with pytest.raises(sut.SyntheticSeedIdentityError, match="different user name"):
        await sut.provision_synthetic_user_portfolio(db, password=PASSWORD)


@pytest.mark.asyncio
async def test_refuses_existing_user_when_password_does_not_match(monkeypatch):
    db = SimpleNamespace()
    monkeypatch.setattr(
        sut.user_service,
        "get_user_by_email",
        AsyncMock(return_value=_user()),
    )
    monkeypatch.setattr(sut, "_load_reserved_portfolios", AsyncMock(return_value=[]))
    monkeypatch.setattr(sut, "verify_password", lambda plain, hashed: False)

    with pytest.raises(sut.SyntheticSeedIdentityError, match="password does not match"):
        await sut.provision_synthetic_user_portfolio(db, password=PASSWORD)


@pytest.mark.asyncio
async def test_refuses_existing_user_with_extra_portfolios(monkeypatch):
    db = SimpleNamespace()
    existing_user = _user()
    canonical = _portfolio()
    extra = _portfolio(id=405, name="unexpected", description=None)

    monkeypatch.setattr(
        sut.user_service,
        "get_user_by_email",
        AsyncMock(return_value=existing_user),
    )
    monkeypatch.setattr(
        sut,
        "_load_reserved_portfolios",
        AsyncMock(return_value=[canonical]),
    )
    monkeypatch.setattr(
        sut.portfolio_service,
        "list_portfolios",
        AsyncMock(return_value=[canonical, extra]),
    )
    monkeypatch.setattr(sut, "verify_password", lambda plain, hashed: True)

    with pytest.raises(sut.SyntheticSeedIdentityError, match="extra portfolios"):
        await sut.provision_synthetic_user_portfolio(db, password=PASSWORD)


@pytest.mark.asyncio
async def test_refuses_portfolio_without_exact_ownership_marker(monkeypatch):
    db = SimpleNamespace()
    existing_user = _user()
    unowned = _portfolio(description="not-owned")

    monkeypatch.setattr(
        sut.user_service,
        "get_user_by_email",
        AsyncMock(return_value=existing_user),
    )
    monkeypatch.setattr(
        sut,
        "_load_reserved_portfolios",
        AsyncMock(return_value=[unowned]),
    )
    monkeypatch.setattr(
        sut.portfolio_service,
        "list_portfolios",
        AsyncMock(return_value=[unowned]),
    )
    monkeypatch.setattr(sut, "verify_password", lambda plain, hashed: True)

    with pytest.raises(sut.SyntheticSeedIdentityError, match="ownership marker"):
        await sut.provision_synthetic_user_portfolio(db, password=PASSWORD)


@pytest.mark.asyncio
async def test_refuses_reserved_portfolio_name_when_synthetic_user_does_not_exist(monkeypatch):
    db = SimpleNamespace()
    monkeypatch.setattr(
        sut.user_service,
        "get_user_by_email",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        sut,
        "_load_reserved_portfolios",
        AsyncMock(return_value=[_portfolio(user_id=999)]),
    )
    create_user = AsyncMock()
    monkeypatch.setattr(sut.user_service, "create_user", create_user)

    with pytest.raises(sut.SyntheticSeedIdentityError, match="another user"):
        await sut.provision_synthetic_user_portfolio(db, password=PASSWORD)

    create_user.assert_not_awaited()
