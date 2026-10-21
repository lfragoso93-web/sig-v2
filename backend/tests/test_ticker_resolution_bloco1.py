from datetime import date
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.asset_alias import AssetAlias
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.asset import AssetCreate
from app.schemas.transaction import TransactionCreate
from app.services.asset_catalog_query_service import suggest_assets_from_catalog
from app.services.asset_service import (
    get_asset_by_ticker,
    get_or_create_asset,
    search_assets,
)
from app.services.transaction_write_service import add_transaction_record


@pytest.mark.asyncio
async def test_get_or_create_asset_resolves_alias_and_prevents_duplication(db: AsyncSession):
    # Setup: Canonical asset BHIA3 with alias VVAR3
    canonical = Asset(
        ticker="BHIA3",
        name="Casas Bahia",
        asset_type=AssetType.ACAO.value,
        currency="BRL",
    )
    db.add(canonical)
    await db.flush()

    alias = AssetAlias(
        asset_id=canonical.id,
        alias_ticker="VVAR3",
        asset_type=AssetType.ACAO.value,
        effective_from=date(2023, 9, 20),
        source_provider="b3",
    )
    db.add(alias)
    await db.flush()

    # When trying to get or create using the old ticker VVAR3
    payload = AssetCreate(
        ticker="VVAR3",
        name="Via Varejo",
        asset_type=AssetType.ACAO,
        currency="BRL",
    )
    asset, is_new = await get_or_create_asset(db, payload)

    # Should resolve to BHIA3 and not create a new row
    assert is_new is False
    assert asset.id == canonical.id
    assert asset.ticker == "BHIA3"


@pytest.mark.asyncio
async def test_get_asset_by_ticker_resolves_alias(db: AsyncSession):
    canonical = Asset(
        ticker="INBR32",
        name="Inter & Co",
        asset_type=AssetType.BDR.value,
        currency="BRL",
    )
    db.add(canonical)
    await db.flush()

    alias = AssetAlias(
        asset_id=canonical.id,
        alias_ticker="BIDI4",
        asset_type=AssetType.BDR.value,
        effective_from=date(2022, 6, 20),
        source_provider="b3",
    )
    db.add(alias)
    await db.flush()

    # Lookup by old ticker
    found = await get_asset_by_ticker(db, "BIDI4")
    assert found is not None
    assert found.id == canonical.id
    assert found.ticker == "INBR32"


@pytest.mark.asyncio
async def test_search_assets_matches_alias(db: AsyncSession):
    canonical = Asset(
        ticker="ALOS3",
        name="Allos",
        asset_type=AssetType.ACAO.value,
        currency="BRL",
    )
    db.add(canonical)
    await db.flush()

    alias = AssetAlias(
        asset_id=canonical.id,
        alias_ticker="BRML3",
        asset_type=AssetType.ACAO.value,
        source_provider="b3",
    )
    db.add(alias)
    await db.flush()

    # Searching by BRML3
    results = await search_assets(db, "BRML3")
    assert any(a.ticker == "ALOS3" for a in results)


@pytest.mark.asyncio
async def test_suggest_assets_from_catalog_annotates_alias(db: AsyncSession):
    canonical = Asset(
        ticker="BHIA3",
        name="Casas Bahia",
        asset_type=AssetType.ACAO.value,
        currency="BRL",
    )
    db.add(canonical)
    await db.flush()

    alias = AssetAlias(
        asset_id=canonical.id,
        alias_ticker="VVAR3",
        asset_type=AssetType.ACAO.value,
        source_provider="b3",
    )
    db.add(alias)
    await db.flush()

    suggestions = await suggest_assets_from_catalog(db, "VVAR3")
    assert len(suggestions) >= 1
    bhia = next(s for s in suggestions if s.ticker == "BHIA3")
    assert "antigo VVAR3" in bhia.name


@pytest.mark.asyncio
async def test_add_transaction_record_resolves_alias_to_canonical_ticker(
    db: AsyncSession,
    user: User,
):
    portfolio = Portfolio(name="Carteira Teste", user_id=user.id)
    db.add(portfolio)
    await db.flush()

    canonical = Asset(
        ticker="BHIA3",
        name="Casas Bahia",
        asset_type=AssetType.ACAO.value,
        currency="BRL",
    )
    db.add(canonical)
    await db.flush()

    alias = AssetAlias(
        asset_id=canonical.id,
        alias_ticker="VVAR3",
        asset_type=AssetType.ACAO.value,
        source_provider="b3",
    )
    db.add(alias)
    await db.flush()

    # Manual buy transaction using old ticker VVAR3
    payload = TransactionCreate(
        portfolio_id=portfolio.id,
        ticker="VVAR3",
        asset_type="ACAO",
        operation="buy",
        quantity=100.0,
        price=10.0,
        date="2023-01-15",
    )
    tx = await add_transaction_record(db, portfolio_id=portfolio.id, payload=payload, flush=True)

    # Recorded transaction must resolve to canonical ticker BHIA3
    assert tx.ticker == "BHIA3"
