from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.asset import AssetType
from app.schemas.asset import AssetCreate, AssetResponse
from app.services.asset_service import get_or_create_asset, search_assets
from app.integrations.brapi import fetch_asset_info
from app.integrations.yfinance_client import fetch_asset_info as yf_fetch_info

router = APIRouter()


# ---------- modelos de resposta -------------------------------------------

class TickerQuoteResponse(BaseModel):
    ticker:     str
    name:       Optional[str]   = None
    price:      Optional[float] = None
    currency:   str             = "BRL"
    asset_type: Optional[str]   = None
    source:     str             = "brapi"   # 'brapi' | 'yfinance' | 'unknown'


# -------  helpers  -----------------------------------------------------------

def _detect_type_from_brapi(info: dict) -> Optional[str]:
    """Infere asset_type pelo campo quoteType da BRAPI."""
    qt = (info.get("quoteType") or "").upper()
    ticker = (info.get("symbol") or "").upper()
    mapping = {
        "EQUITY":   "ACAO",
        "ETF":      "ETF_NACIONAL",
        "FUND":     "FII",
        "MUTUALFUND": "FII",
    }
    detected = mapping.get(qt)
    # FIIs terminam em 11 em geral
    if not detected and ticker.endswith("11"):
        detected = "FII"
    return detected


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
    Retorna cotação atual + metadados de um ticker.
    Tenta BRAPI primeiro (ativos BR); fallback para yfinance (stocks/ETFs internacionais).
    Usado pelo modal de lançamento para autocompletar preço e nome.
    """
    t = ticker.strip().upper()

    # --- tenta BRAPI (mercado brasileiro) ---
    info = await fetch_asset_info(t)
    if info and info.get("regularMarketPrice"):
        return TickerQuoteResponse(
            ticker     = t,
            name       = info.get("longName") or info.get("shortName"),
            price      = float(info["regularMarketPrice"]),
            currency   = info.get("currency") or "BRL",
            asset_type = _detect_type_from_brapi(info),
            source     = "brapi",
        )

    # --- fallback: yfinance (internacionais) ---
    try:
        yf_info = await yf_fetch_info(t)
        if yf_info and yf_info.get("price"):
            return TickerQuoteResponse(
                ticker     = t,
                name       = yf_info.get("name"),
                price      = float(yf_info["price"]),
                currency   = yf_info.get("currency") or "USD",
                asset_type = yf_info.get("asset_type"),
                source     = "yfinance",
            )
    except Exception:
        pass

    # --- não encontrado ---
    raise HTTPException(status_code=404, detail=f"Ticker '{t}' não encontrado.")
