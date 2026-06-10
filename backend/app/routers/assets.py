from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.asset import AssetType
from app.schemas.asset import AssetCreate, AssetResponse
from app.services.asset_service import get_or_create_asset, search_assets
from app.integrations.brapi import fetch_asset_info

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------- modelos de resposta -------------------------------------------

class TickerQuoteResponse(BaseModel):
    ticker:     str
    name:       Optional[str]   = None
    price:      Optional[float] = None
    currency:   str             = "BRL"
    asset_type: Optional[str]   = None
    source:     str             = "brapi"


# ---------- helpers -----------------------------------------------------------

def _detect_type_from_brapi(info: dict) -> Optional[str]:
    qt = (info.get("quoteType") or "").upper()
    ticker = (info.get("symbol") or "").upper()
    mapping = {
        "EQUITY": "ACAO",
        "ETF": "ETF_NACIONAL",
        "FUND": "FII",
        "MUTUALFUND": "FII",
    }
    detected = mapping.get(qt)
    if not detected and ticker.endswith("11"):
        detected = "FII"
    return detected


def _yf_fetch_sync(ticker: str) -> Optional[dict]:
    """Busca info via yfinance em thread (não bloqueia o event loop)."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        info = t.info
        price = (
            info.get("regularMarketPrice")
            or info.get("currentPrice")
            or info.get("previousClose")
        )
        if not price:
            return None
        qt = (info.get("quoteType") or "").upper()
        asset_map = {
            "EQUITY": "STOCK",
            "ETF": "ETF_INTERNACIONAL",
            "CRYPTOCURRENCY": "CRIPTO",
        }
        return {
            "price":      float(price),
            "name":       info.get("longName") or info.get("shortName"),
            "currency":   (info.get("currency") or "USD").upper(),
            "asset_type": asset_map.get(qt),
        }
    except Exception as e:
        logger.warning(f"yfinance fetch error for {ticker}: {e}")
        return None


async def _yf_fetch_async(ticker: str) -> Optional[dict]:
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as pool:
        return await loop.run_in_executor(pool, _yf_fetch_sync, ticker)


# ---------- endpoints ---------------------------------------------------------

@router.get("/search", response_model=list[AssetResponse])
async def search_assets_endpoint(
    q: str = Query("", min_length=1),
    asset_type: Optional[AssetType] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Busca ativos por ticker ou nome."""
    return await search_assets(db, q, asset_type, limit)


@router.post("/", response_model=AssetResponse)
async def upsert_asset(
    data: AssetCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Cria ou retorna ativo existente (ticker + tipo é único)."""
    return await get_or_create_asset(db, data)


@router.get("/quote/{ticker}", response_model=TickerQuoteResponse)
async def get_ticker_quote(
    ticker: str,
    _=Depends(get_current_user),
):
    """
    Cotação atual + metadados de um ticker.
    Tenta BRAPI primeiro (ativos BR); fallback yfinance (stocks/ETFs internacionais).
    """
    t = ticker.strip().upper()

    # --- BRAPI (mercado brasileiro) ---
    info = await fetch_asset_info(t)
    if info and info.get("regularMarketPrice"):
        return TickerQuoteResponse(
            ticker     = t,
            name       = info.get("longName") or info.get("shortName"),
            price      = float(info["regularMarketPrice"]),
            currency   = (info.get("currency") or "BRL").upper(),
            asset_type = _detect_type_from_brapi(info),
            source     = "brapi",
        )

    # --- yfinance fallback (internacionais) ---
    yf_info = await _yf_fetch_async(t)
    if yf_info and yf_info.get("price"):
        return TickerQuoteResponse(
            ticker     = t,
            name       = yf_info.get("name"),
            price      = yf_info["price"],
            currency   = yf_info.get("currency", "USD"),
            asset_type = yf_info.get("asset_type"),
            source     = "yfinance",
        )

    raise HTTPException(status_code=404, detail=f"Ticker '{t}' não encontrado.")
