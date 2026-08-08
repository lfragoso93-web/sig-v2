from datetime import date as date_type
import logging
import math
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.asset import Asset, AssetType
from app.schemas.asset import AssetCreate, AssetResponse
from app.services import csv_import_service
from app.services.asset_catalog_query_service import (
    list_treasury_from_catalog,
    suggest_assets_from_catalog,
)
from app.services.asset_service import get_or_create_asset, search_assets
from app.services.price_date_gap_resolver_service import resolve_price_at_date_gap
from app.services.price_service import get_current_price, get_price_history

logger = logging.getLogger(__name__)
router = APIRouter()

_CRYPTO_NAME_TO_TICKER: dict[str, str] = {
    "BITCOIN": "BTC",
    "ETHEREUM": "ETH",
    "CARDANO": "ADA",
    "SOLANA": "SOL",
    "RIPPLE": "XRP",
    "DOGECOIN": "DOGE",
    "POLKADOT": "DOT",
    "LITECOIN": "LTC",
    "CHAINLINK": "LINK",
    "UNISWAP": "UNI",
    "AVALANCHE": "AVAX",
    "POLYGON": "MATIC",
    "BINANCECOIN": "BNB",
    "TETHER": "USDT",
    "USDCOIN": "USDC",
    "STELLAR": "XLM",
    "TRON": "TRX",
    "MONERO": "XMR",
    "COSMOS": "ATOM",
    "ALGORAND": "ALGO",
}


class TickerQuoteResponse(BaseModel):
    ticker: str
    name: Optional[str] = None
    price: Optional[float] = None
    currency: str = "BRL"
    asset_type: Optional[str] = None
    source: str = "asset_prices"
    price_date: Optional[str] = None


class TreasuryItem(BaseModel):
    name: str
    ticker: str
    slug: Optional[str] = None
    indexer: str
    rate: Optional[float] = None
    maturity_date: Optional[str] = None
    price: Optional[float] = None


class TreasuryPriceResponse(BaseModel):
    slug: str
    price: Optional[float]
    price_date: str
    source: str = "asset_prices"


class TickerSuggestion(BaseModel):
    ticker: str
    name: str
    type: Optional[str] = None


class AssetListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    name: Optional[str] = None
    asset_type: str
    last_price: Optional[float] = None
    last_price_updated_at: Optional[str] = None


class AssetListResponse(BaseModel):
    items: list[AssetListItem]
    total: int
    page: int
    page_size: int
    pages: int


class PricePoint(BaseModel):
    date: str
    close: float


class AssetDetailResponse(BaseModel):
    id: int
    ticker: str
    name: Optional[str] = None
    asset_type: str
    last_price: Optional[float] = None
    last_price_updated_at: Optional[str] = None
    current_price: Optional[float] = None
    price_history: list[PricePoint] = []


def _treasury_indexer(value: str) -> str:
    upper = value.upper()
    if "SELIC" in upper:
        return "SELIC"
    if "IPCA" in upper or "RENDA" in upper or "EDUCA" in upper:
        return "IPCA+"
    if "IGP" in upper:
        return "IGP-M"
    return "Prefixado"


def _treasury_maturity_from_ticker(ticker: str) -> Optional[str]:
    match = re.search(r"(\d{2})(\d{2})(20\d{2})$", ticker)
    if not match:
        return None
    day, month, year = match.groups()
    try:
        return date_type(int(year), int(month), int(day)).isoformat()
    except ValueError:
        return None


def _crypto_candidate(ticker: str) -> str:
    normalized = ticker.strip().upper()
    return _CRYPTO_NAME_TO_TICKER.get(normalized, normalized)


async def _find_catalog_asset(
    db: AsyncSession,
    ticker: str,
    asset_type: Optional[str] = None,
) -> Optional[Asset]:
    normalized = ticker.strip().upper()
    candidates = {normalized, _crypto_candidate(normalized)}
    stmt = select(Asset).where(func.upper(Asset.ticker).in_(candidates))
    if asset_type:
        stmt = stmt.where(Asset.asset_type == asset_type.strip().upper())
    stmt = stmt.order_by(
        case((func.upper(Asset.ticker) == normalized, 0), else_=1),
        Asset.id,
    ).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


@router.get("/", response_model=AssetListResponse)
async def list_assets(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    asset_type: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    stmt = select(Asset)
    if asset_type:
        stmt = stmt.where(Asset.asset_type == asset_type.upper())
    if q and q.strip():
        q_like = f"%{q.strip().upper()}%"
        stmt = stmt.where(
            or_(
                func.upper(Asset.ticker).like(q_like),
                func.upper(func.coalesce(Asset.name, "")).like(q_like),
            )
        )

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = stmt.order_by(Asset.ticker).offset((page - 1) * page_size).limit(page_size)
    assets = (await db.execute(stmt)).scalars().all()
    return AssetListResponse(
        items=[
            AssetListItem(
                id=asset.id,
                ticker=asset.ticker,
                name=asset.name,
                asset_type=str(asset.asset_type),
                last_price=float(asset.last_price) if asset.last_price else None,
                last_price_updated_at=(
                    asset.last_price_updated_at.isoformat()
                    if asset.last_price_updated_at
                    else None
                ),
            )
            for asset in assets
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/{ticker}/detail", response_model=AssetDetailResponse)
async def get_asset_detail(
    ticker: str,
    days: int = Query(90, ge=7, le=1825),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    asset = await _find_catalog_asset(db, ticker)
    if asset is None:
        raise HTTPException(status_code=404, detail=f"Ativo '{ticker.upper()}' nao encontrado no banco.")

    asset_type = AssetType(str(asset.asset_type))
    current_price: Optional[float] = None
    try:
        current_price = await get_current_price(
            ticker=asset.ticker,
            asset_type=asset_type.value,
            db=db,
        )
    except Exception as exc:
        logger.warning("[assets] cotacao intraday falhou para %s: %s", asset.ticker, exc)

    history = await get_price_history(
        db=db,
        ticker=asset.ticker,
        asset_type=asset_type,
        days=days,
    )
    return AssetDetailResponse(
        id=asset.id,
        ticker=asset.ticker,
        name=asset.name,
        asset_type=asset_type.value,
        last_price=float(asset.last_price) if asset.last_price else None,
        last_price_updated_at=(
            asset.last_price_updated_at.isoformat() if asset.last_price_updated_at else None
        ),
        current_price=current_price,
        price_history=[PricePoint(**point) for point in history],
    )


@router.get("/search", response_model=list[AssetResponse])
async def search_assets_endpoint(
    q: str = Query("", min_length=1),
    asset_type: Optional[AssetType] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await search_assets(db, q, asset_type, limit)


@router.post("/", response_model=AssetResponse)
async def upsert_asset(
    data: AssetCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await get_or_create_asset(db, data)


@router.get("/suggest", response_model=list[TickerSuggestion])
async def suggest_tickers(
    q: str = Query("", min_length=2),
    limit: int = Query(10, ge=1, le=20),
    asset_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    items = await suggest_assets_from_catalog(
        db,
        q,
        limit=limit,
        asset_type=asset_type,
    )
    return [
        TickerSuggestion(ticker=item.ticker, name=item.name, type=item.asset_type)
        for item in items
    ]


@router.get("/tesouro/search", response_model=list[TreasuryItem])
async def search_treasury(
    q: str = Query("", min_length=0),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    items = await list_treasury_from_catalog(db, q)
    return [
        TreasuryItem(
            name=item.name,
            ticker=item.ticker,
            slug=item.ticker,
            indexer=_treasury_indexer(item.name),
            maturity_date=_treasury_maturity_from_ticker(item.ticker),
        )
        for item in items
    ]


@router.get("/tesouro/price", response_model=TreasuryPriceResponse)
async def get_treasury_price(
    slug: str = Query(...),
    date: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    asset = await _find_catalog_asset(db, slug, AssetType.TESOURO_DIRETO.value)
    if asset is None:
        raise HTTPException(status_code=404, detail=f"Titulo '{slug}' nao encontrado no catalogo.")

    today = date_type.today().isoformat()
    if date == today:
        price = await get_current_price(
            ticker=asset.ticker,
            asset_type=AssetType.TESOURO_DIRETO.value,
            db=db,
        )
        source = "market_data_provider"
    else:
        price = await resolve_price_at_date_gap(
            db,
            asset.ticker,
            AssetType.TESOURO_DIRETO,
            date,
        )
        source = "asset_prices"

    return TreasuryPriceResponse(slug=slug, price=price, price_date=date, source=source)


@router.get("/quote/{ticker}", response_model=TickerQuoteResponse)
async def get_ticker_quote(
    ticker: str,
    date: Optional[str] = Query(None),
    asset_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    asset = await _find_catalog_asset(db, ticker, asset_type)
    if asset is None:
        raise HTTPException(
            status_code=404,
            detail=f"Ticker '{ticker.upper()}' nao encontrado no catalogo persistido.",
        )

    normalized_type = AssetType(str(asset.asset_type))
    today = date_type.today().isoformat()
    requested_date = date or today

    if requested_date != today:
        price = await resolve_price_at_date_gap(
            db,
            asset.ticker,
            normalized_type,
            requested_date,
        )
        source = "asset_prices"
    else:
        price = await get_current_price(
            ticker=asset.ticker,
            asset_type=normalized_type.value,
            db=db,
        )
        source = "market_data_provider"

    if price is None:
        raise HTTPException(
            status_code=404,
            detail=f"Cotacao nao encontrada para '{asset.ticker}' em {requested_date}.",
        )

    return TickerQuoteResponse(
        ticker=asset.ticker,
        name=asset.name,
        price=float(price),
        currency=str(asset.currency or "BRL"),
        asset_type=normalized_type.value,
        source=source,
        price_date=requested_date,
    )


@router.get("/csv-template", tags=["csv-import"])
async def get_csv_template():
    csv_content = csv_import_service.generate_csv_template()
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="portfolio_import_template.csv"'},
    )
