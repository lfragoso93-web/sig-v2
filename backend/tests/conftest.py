import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.portfolio import Portfolio
from app.models.transaction import Transaction, OperationType  # noqa: F401
from app.models.portfolio_position import PortfolioPosition  # noqa: F401

# Import Base de todos os modelos para criar as tabelas no SQLite de teste
from app.models.user import User
from app.models.asset import Asset
from app.models.dividend import Dividend

DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db():
    """
    Sessão AsyncSession com SQLite em memória.
    Cria todas as tabelas antes de cada teste e faz rollback ao final.
    """
    engine = create_async_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Importa todos os modelos para garantir que Base.metadata os conhece
    from app.core.database import Base  # noqa: F401 — registra metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def user(db: AsyncSession) -> User:
    u = User(name="Teste", email="teste@sig.com", hashed_password="hash", is_active=True)
    db.add(u)
    await db.flush()
    await db.refresh(u)
    return u


@pytest_asyncio.fixture
async def portfolio(db: AsyncSession, user: User) -> Portfolio:
    p = Portfolio(user_id=user.id, name="Carteira Teste", description="")
    db.add(p)
    await db.flush()
    await db.refresh(p)
    return p
