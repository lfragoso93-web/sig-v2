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
from app.integrations.brapi import fetch_asset_info, fetch_historical_price, fetch_treasury_list

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------- modelos de resposta -------------------------------------------

class TickerQuoteResponse(BaseModel):
    ticker:      str
    name:        Optional[str]   = None
    price:       Optional[float] = None
    currency:    str             = "BRL"
    asset_type:  Optional[str]   = None
    source:      str             = "brapi"
    price_date:  Optional[str]   = None


class TreasuryItem(BaseModel):
    name:          str
    ticker:        str
    indexer:       str
    rate:          Optional[float] = None
    maturity_date: Optional[str]   = None
    price:         Optional[float] = None


# ---------- helpers -----------------------------------------------------------

def _detect_type_from_brapi(info: dict) -> Optional[str]:
    qt     = (info.get("quoteType") or "").upper()
    ticker = (info.get("symbol") or "").upper()
    mapping = {
        "EQUITY":     "ACAO",
        "ETF":        "ETF_NACIONAL",
        "FUND":       "FII",
        "MUTUALFUND": "FII",
    }
    detected = mapping.get(qt)
    if not detected and ticker.endswith("11"):
        detected = "FII"
    return detected


def _yf_fetch_sync(ticker: str, date_str: Optional[str] = None) -> Optional[dict]:
    """Busca info via yfinance em thread."""
    try:
        import yfinance as yf
        from datetime import date, timedelta

        t = yf.Ticker(ticker)

        if date_str:
            ref   = date.fromisoformat(date_str)
            start = (ref - timedelta(days=5)).isoformat()
            end   = (ref + timedelta(days=1)).isoformat()
            hist  = t.history(start=start, end=end, interval="1d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
            else:
                price = None
        else:
            info  = t.info
            price = (
                info.get("regularMarketPrice")
                or info.get("currentPrice")
                or info.get("previousClose")
            )
            if price:
                price = float(price)

        if not price:
            return None

        info = t.info
        qt   = (info.get("quoteType") or "").upper()
        asset_map = {
            "EQUITY":         "STOCK",
            "ETF":            "ETF_INTERNACIONAL",
            "CRYPTOCURRENCY": "CRIPTO",
        }
        return {
            "price":      price,
            "name":       info.get("longName") or info.get("shortName"),
            "currency":   (info.get("currency") or "USD").upper(),
            "asset_type": asset_map.get(qt),
        }
    except Exception as e:
        logger.warning(f"yfinance fetch error for {ticker}: {e}")
        return None


async def _yf_fetch_async(ticker: str, date_str: Optional[str] = None) -> Optional[dict]:
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as pool:
        return await loop.run_in_executor(pool, _yf_fetch_sync, ticker, date_str)


def _parse_treasury_item(raw: dict) -> Optional[TreasuryItem]:
    """
    Normaliza um item da resposta BRAPI /v2/treasury/list para TreasuryItem.
    Campos da API v2: symbol, bondType, indexer, buyRate, sellRate,
                      buyPrice, sellPrice, basePrice, maturityDate, couponType, durationDays.
    """
    # Nome legivel do titulo (ex: "Tesouro IPCA+ com Juros Semestrais")
    bond_type = raw.get("bondType") or raw.get("name") or raw.get("shortName") or ""
    if not bond_type:
        return None

    # Data de vencimento (campo maturityDate vem como YYYY-MM-DD)
    maturity = raw.get("maturityDate") or raw.get("expirationDate") or ""
    if maturity:
        try:
            if isinstance(maturity, (int, float)):
                from datetime import datetime
                maturity = datetime.utcfromtimestamp(maturity).strftime("%Y-%m-%d")
        except Exception:
            pass
        maturity = str(maturity)[:10]
    else:
        maturity = None

    # Nome completo para exibicao (ex: "Tesouro IPCA+ 2029")
    year = maturity[:4] if maturity else ""
    display_name = f"{bond_type} {year}".strip() if year else bond_type

    # Ticker slug (symbol) ou display_name como fallback
    ticker = raw.get("symbol") or display_name

    # Indexador: usa campo 'indexer' da API (selic / prefixado / ipca / igpm)
    indexer_raw = (raw.get("indexer") or "").lower()
    bond_upper  = bond_type.upper()
    if indexer_raw == "ipca" or "IPCA" in bond_upper:
        indexer = "IPCA+"
    elif indexer_raw == "selic" or "SELIC" in bond_upper:
        indexer = "SELIC"
    elif indexer_raw in ("prefixado", "pre") or "PREFIXADO" in bond_upper:
        indexer = "Prefixado"
    elif indexer_raw == "igpm" or "IGP" in bond_upper:
        indexer = "IGP-M"
    else:
        indexer = "Prefixado"

    # Taxa: buyRate (% a.a.) — para Selic e o spread, nao a taxa total
    rate = raw.get("buyRate") or raw.get("sellRate")
    try:
        rate = float(rate) if rate is not None else None
    except (ValueError, TypeError):
        rate = None

    # Preco unitario de compra
    price = raw.get("buyPrice") or raw.get("basePrice") or raw.get("sellPrice")
    try:
        price = float(price) if price is not None else None
    except (ValueError, TypeError):
        price = None

    return TreasuryItem(
        name=display_name,
        ticker=ticker,
        indexer=indexer,
        rate=rate,
        maturity_date=maturity,
        price=price,
    )


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
    """Cria ou retorna ativo existente (ticker + tipo e unico)."""
    return await get_or_create_asset(db, data)


@router.get("/tesouro/search", response_model=list[TreasuryItem])
async def search_treasury(
    q: str = Query("", min_length=0),
    _=Depends(get_current_user),
):
    """
    Busca titulos do Tesouro Direto via BRAPI /v2/treasury/list.
    Filtra pelo parametro q (busca no nome do titulo).
    Requer plano Pro na BRAPI; sem token retorna apenas 3 titulos sandbox.
    """
    items = await fetch_treasury_list()
    parsed = [_parse_treasury_item(i) for i in items]
    parsed = [i for i in parsed if i is not None]

    if q.strip():
        q_lower = q.strip().lower()
        parsed = [i for i in parsed if q_lower in i.name.lower() or q_lower in i.ticker.lower()]

    return parsed


@router.get("/quote/{ticker}", response_model=TickerQuoteResponse)
async def get_ticker_quote(
    ticker: str,
    date: Optional[str] = Query(None, description="Data no formato YYYY-MM-DD para preco historico"),
    _=Depends(get_current_user),
):
    """
    Cotacao de um ticker em uma data especifica (ou atual se date omitido).
    Tenta BRAPI primeiro; fallback yfinance para internacionais.
    """
    t        = ticker.strip().upper()
    today    = __import__('datetime').date.today().isoformat()
    use_hist = date and date != today

    # --- BRAPI historico ---
    if use_hist:
        hist_price = await fetch_historical_price(t, date)
        if hist_price:
            return TickerQuoteResponse(
                ticker     = t,
                price      = hist_price,
                currency   = "BRL",
                source     = "brapi",
                price_date = date,
            )

    # --- BRAPI atual ---
    info = await fetch_asset_info(t)
    if info and info.get("regularMarketPrice"):
        return TickerQuoteResponse(
            ticker     = t,
            name       = info.get("longName") or info.get("shortName"),
            price      = float(info["regularMarketPrice"]),
            currency   = (info.get("currency") or "BRL").upper(),
            asset_type = _detect_type_from_brapi(info),
            source     = "brapi",
            price_date = today,
        )

    # --- yfinance fallback (internacionais / historico) ---
    yf_info = await _yf_fetch_async(t, date if use_hist else None)
    if yf_info and yf_info.get("price"):
        return TickerQuoteResponse(
            ticker     = t,
            name       = yf_info.get("name"),
            price      = yf_info["price"],
            currency   = yf_info.get("currency", "USD"),
            asset_type = yf_info.get("asset_type"),
            source     = "yfinance",
            price_date = date or today,
        )

    raise HTTPException(status_code=404, detail=f"Ticker '{t}' nao encontrado.")
