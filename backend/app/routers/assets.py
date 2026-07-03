from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel
import asyncio
import io
from concurrent.futures import ThreadPoolExecutor
import logging

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.asset import Asset, AssetType
from app.schemas.asset import AssetCreate, AssetResponse
from app.services.asset_service import get_or_create_asset, search_assets
from app.services.price_service import get_current_price, get_price_history
from app.services import csv_import_service
from app.integrations.brapi import (
    fetch_asset_info,
    fetch_historical_price,
    fetch_treasury_list,
    fetch_ticker_suggestions,
    fetch_treasury_price_by_date,
    fetch_crypto_suggestions,
    fetch_crypto_quote,
    _normalize_crypto_ticker,
    _yf_search_sync,
)

logger = logging.getLogger(__name__)

router = APIRouter()


_TESOURO_STATIC: list[dict] = [
    {"bondType": "Tesouro Selic", "indexer": "selic", "maturityDate": "2026-03-01", "slug": "tesouro-selic-01032026"},
    {"bondType": "Tesouro Selic", "indexer": "selic", "maturityDate": "2027-03-01", "slug": "tesouro-selic-01032027"},
    {"bondType": "Tesouro Selic", "indexer": "selic", "maturityDate": "2029-03-01", "slug": "tesouro-selic-01032029"},
    {"bondType": "Tesouro Selic", "indexer": "selic", "maturityDate": "2031-03-01", "slug": "tesouro-selic-01032031"},
    {"bondType": "Tesouro Prefixado", "indexer": "prefixado", "maturityDate": "2027-01-01", "slug": "tesouro-prefixado-01012027"},
    {"bondType": "Tesouro Prefixado", "indexer": "prefixado", "maturityDate": "2029-01-01", "slug": "tesouro-prefixado-01012029"},
    {"bondType": "Tesouro Prefixado", "indexer": "prefixado", "maturityDate": "2031-01-01", "slug": "tesouro-prefixado-01012031"},
    {"bondType": "Tesouro Prefixado com Juros Semestrais", "indexer": "prefixado", "maturityDate": "2033-01-01", "slug": "tesouro-prefixado-com-juros-semestrais-01012033"},
    {"bondType": "Tesouro Prefixado com Juros Semestrais", "indexer": "prefixado", "maturityDate": "2035-01-01", "slug": "tesouro-prefixado-com-juros-semestrais-01012035"},
    {"bondType": "Tesouro IPCA+", "indexer": "ipca", "maturityDate": "2029-05-15", "slug": "tesouro-ipca-15052029"},
    {"bondType": "Tesouro IPCA+", "indexer": "ipca", "maturityDate": "2032-08-15", "slug": "tesouro-ipca-15082032"},
    {"bondType": "Tesouro IPCA+", "indexer": "ipca", "maturityDate": "2035-05-15", "slug": "tesouro-ipca-15052035"},
    {"bondType": "Tesouro IPCA+", "indexer": "ipca", "maturityDate": "2045-05-15", "slug": "tesouro-ipca-15052045"},
    {"bondType": "Tesouro IPCA+ com Juros Semestrais", "indexer": "ipca", "maturityDate": "2030-08-15", "slug": "tesouro-ipca-com-juros-semestrais-15082030"},
    {"bondType": "Tesouro IPCA+ com Juros Semestrais", "indexer": "ipca", "maturityDate": "2040-08-15", "slug": "tesouro-ipca-com-juros-semestrais-15082040"},
    {"bondType": "Tesouro IPCA+ com Juros Semestrais", "indexer": "ipca", "maturityDate": "2055-05-15", "slug": "tesouro-ipca-com-juros-semestrais-15052055"},
    {"bondType": "Tesouro IPCA+ com Juros Semestrais", "indexer": "ipca", "maturityDate": "2060-08-15", "slug": "tesouro-ipca-com-juros-semestrais-15082060"},
    {"bondType": "Tesouro Renda+ Aposentadoria Extra", "indexer": "ipca", "maturityDate": "2030-12-01", "slug": "tesouro-renda-aposentadoria-extra-01122030"},
    {"bondType": "Tesouro Renda+ Aposentadoria Extra", "indexer": "ipca", "maturityDate": "2035-12-01", "slug": "tesouro-renda-aposentadoria-extra-01122035"},
    {"bondType": "Tesouro Renda+ Aposentadoria Extra", "indexer": "ipca", "maturityDate": "2040-12-01", "slug": "tesouro-renda-aposentadoria-extra-01122040"},
    {"bondType": "Tesouro Renda+ Aposentadoria Extra", "indexer": "ipca", "maturityDate": "2045-12-01", "slug": "tesouro-renda-aposentadoria-extra-01122045"},
    {"bondType": "Tesouro Renda+ Aposentadoria Extra", "indexer": "ipca", "maturityDate": "2050-12-01", "slug": "tesouro-renda-aposentadoria-extra-01122050"},
    {"bondType": "Tesouro Renda+ Aposentadoria Extra", "indexer": "ipca", "maturityDate": "2055-12-01", "slug": "tesouro-renda-aposentadoria-extra-01122055"},
    {"bondType": "Tesouro Renda+ Aposentadoria Extra", "indexer": "ipca", "maturityDate": "2060-12-01", "slug": "tesouro-renda-aposentadoria-extra-01122060"},
    {"bondType": "Tesouro Renda+ Aposentadoria Extra", "indexer": "ipca", "maturityDate": "2065-12-01", "slug": "tesouro-renda-aposentadoria-extra-01122065"},
    {"bondType": "Tesouro Educa+", "indexer": "ipca", "maturityDate": "2026-12-01", "slug": "tesouro-educa-01122026"},
    {"bondType": "Tesouro Educa+", "indexer": "ipca", "maturityDate": "2030-12-01", "slug": "tesouro-educa-01122030"},
    {"bondType": "Tesouro Educa+", "indexer": "ipca", "maturityDate": "2035-12-01", "slug": "tesouro-educa-01122035"},
    {"bondType": "Tesouro Educa+", "indexer": "ipca", "maturityDate": "2037-12-01", "slug": "tesouro-educa-01122037"},
]

_SLUG_INDEX: dict[str, dict] = {item["slug"]: item for item in _TESOURO_STATIC if "slug" in item}

# Mapa nome-completo -> ticker para criptos comuns.
# Usado como fallback quando o banco tem ticker=BITCOIN em vez de BTC.
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


# ---------------------------------------------------------------------------
# Schemas locais
# ---------------------------------------------------------------------------

class TickerQuoteResponse(BaseModel):
    ticker: str
    name: Optional[str] = None
    price: Optional[float] = None
    currency: str = "BRL"
    asset_type: Optional[str] = None
    source: str = "brapi"
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
    source: str = "brapi"


class TickerSuggestion(BaseModel):
    ticker: str
    name: str
    type: Optional[str] = None


class AssetListItem(BaseModel):
    id: int
    ticker: str
    name: Optional[str] = None
    asset_type: str
    last_price: Optional[float] = None
    last_price_updated_at: Optional[str] = None

    class Config:
        from_attributes = True


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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _resolve_crypto_ticker(ticker: str, db_asset_type: Optional[str] = None) -> Optional[str]:
    """
    Tenta resolver o ticker de uma cripto para o codigo BRAPI.
    Retorna o codigo normalizado se for cripto, ou None se nao for cripto.

    Casos tratados:
      - ticker ja e o codigo (BTC, ETH, ADA) -> retorna normalizado
      - ticker e nome completo (BITCOIN, ETHEREUM) -> faz lookup no mapa
      - db_asset_type == 'CRIPTO' -> forca tratamento como cripto
    """
    t = ticker.strip().upper()

    # Se o asset_type do banco diz CRIPTO, tenta resolver
    is_cripto = (db_asset_type or "").upper() == "CRIPTO"

    # Lookup por nome completo primeiro
    if t in _CRYPTO_NAME_TO_TICKER:
        return _CRYPTO_NAME_TO_TICKER[t]

    # Se vier de contexto cripto, normaliza o ticker (remove sufixos -USD, BRL, etc)
    if is_cripto:
        return _normalize_crypto_ticker(t)

    return None


def _yf_fetch_sync(ticker: str, date_str: Optional[str] = None) -> Optional[dict]:
    try:
        import yfinance as yf
        from datetime import date, timedelta
        t = yf.Ticker(ticker)
        if date_str:
            ref = date.fromisoformat(date_str)
            start = (ref - timedelta(days=5)).isoformat()
            end = (ref + timedelta(days=1)).isoformat()
            hist = t.history(start=start, end=end, interval="1d")
            price = float(hist["Close"].iloc[-1]) if not hist.empty else None
        else:
            info = t.info
            price = info.get("regularMarketPrice") or info.get("currentPrice") or info.get("previousClose")
            price = float(price) if price else None
        if not price:
            return None
        info = t.info
        qt = (info.get("quoteType") or "").upper()
        asset_map = {
            "EQUITY": "STOCK", "ETF": "ETF_INTERNACIONAL", "CRYPTOCURRENCY": "CRIPTO",
        }
        return {
            "price": price,
            "name": info.get("longName") or info.get("shortName"),
            "currency": (info.get("currency") or "USD").upper(),
            "asset_type": asset_map.get(qt),
        }
    except Exception as e:
        logger.warning(f"yfinance fetch error for {ticker}: {e}")
        return None


async def _yf_fetch_async(ticker: str, date_str: Optional[str] = None) -> Optional[dict]:
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as pool:
        return await loop.run_in_executor(pool, _yf_fetch_sync, ticker, date_str)


async def _yf_search_async(q: str, limit: int = 10, asset_type: Optional[str] = None) -> list[dict]:
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as pool:
        return await loop.run_in_executor(pool, _yf_search_sync, q, limit, asset_type)


def _parse_treasury_item(raw: dict) -> Optional[TreasuryItem]:
    bond_type = raw.get("bondType") or raw.get("name") or raw.get("shortName") or ""
    if not bond_type:
        return None

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

    year = maturity[:4] if maturity else ""
    display_name = f"{bond_type} {year}".strip() if year else bond_type
    slug = raw.get("slug") or raw.get("symbol")
    ticker = slug or display_name

    indexer_raw = (raw.get("indexer") or "").lower()
    bond_upper = bond_type.upper()
    if indexer_raw == "ipca" or "IPCA" in bond_upper or "RENDA+" in bond_upper or "EDUCA+" in bond_upper:
        indexer = "IPCA+"
    elif indexer_raw == "selic" or "SELIC" in bond_upper:
        indexer = "SELIC"
    elif indexer_raw in ("prefixado", "pre") or "PREFIXADO" in bond_upper:
        indexer = "Prefixado"
    elif indexer_raw == "igpm" or "IGP" in bond_upper:
        indexer = "IGP-M"
    else:
        indexer = "Prefixado"

    rate = raw.get("buyRate") or raw.get("sellRate")
    try:
        rate = float(rate) if rate is not None else None
    except (ValueError, TypeError):
        rate = None

    price = raw.get("buyPrice") or raw.get("basePrice") or raw.get("sellPrice")
    try:
        price = float(price) if price is not None else None
    except (ValueError, TypeError):
        price = None

    return TreasuryItem(
        name=display_name,
        ticker=ticker,
        slug=slug,
        indexer=indexer,
        rate=rate,
        maturity_date=maturity,
        price=price,
    )


# ---------------------------------------------------------------------------
# GET /assets/  — listagem paginada
# ---------------------------------------------------------------------------

@router.get("/", response_model=AssetListResponse)
async def list_assets(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    asset_type: Optional[str] = Query(None, description="Filtro por tipo: ACAO, FII, ETF_NACIONAL, BDR, STOCK, ETF_INTERNACIONAL, CRIPTO, TESOURO_DIRETO, RENDA_FIXA"),
    q: Optional[str] = Query(None, description="Busca por ticker ou nome (case-insensitive)"),
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
                func.upper(Asset.name).like(q_like),
            )
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = stmt.order_by(Asset.ticker).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    assets = result.scalars().all()

    items = [
        AssetListItem(
            id=a.id,
            ticker=a.ticker,
            name=a.name,
            asset_type=str(a.asset_type),
            last_price=float(a.last_price) if a.last_price else None,
            last_price_updated_at=a.last_price_updated_at.isoformat() if a.last_price_updated_at else None,
        )
        for a in assets
    ]

    import math
    return AssetListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
    )


# ---------------------------------------------------------------------------
# GET /assets/{ticker}/detail
# ---------------------------------------------------------------------------

@router.get("/{ticker}/detail", response_model=AssetDetailResponse)
async def get_asset_detail(
    ticker: str,
    days: int = Query(90, ge=7, le=1825, description="Dias de historico de precos (7-1825)"),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    t = ticker.strip().upper()

    result = await db.execute(select(Asset).where(Asset.ticker == t))
    asset = result.scalar_one_or_none()

    if asset is None:
        raise HTTPException(status_code=404, detail=f"Ativo '{t}' nao encontrado no banco.")

    asset_type_str = str(asset.asset_type)

    current_price: Optional[float] = None
    try:
        current_price = await get_current_price(
            ticker=t,
            asset_type=asset_type_str,
            db=db,
        )
    except Exception as e:
        logger.warning(f"[assets] get_current_price falhou para {t}: {e}")

    history: list[dict] = []
    try:
        asset_type_enum = AssetType(asset_type_str)
        history = await get_price_history(db=db, ticker=t, asset_type=asset_type_enum, days=days)
    except Exception as e:
        logger.warning(f"[assets] get_price_history falhou para {t}: {e}")

    return AssetDetailResponse(
        id=asset.id,
        ticker=asset.ticker,
        name=asset.name,
        asset_type=asset_type_str,
        last_price=float(asset.last_price) if asset.last_price else None,
        last_price_updated_at=asset.last_price_updated_at.isoformat() if asset.last_price_updated_at else None,
        current_price=current_price,
        price_history=[PricePoint(**p) for p in history],
    )


# ---------------------------------------------------------------------------
# Endpoints de escrita / busca
# ---------------------------------------------------------------------------

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
    _=Depends(get_current_user),
):
    if asset_type == "cripto":
        raw = await fetch_crypto_suggestions(q.strip(), limit)
        result = []
        for item in raw:
            # A BRAPI /crypto/available pode retornar:
            #   - lista de strings: ["BTC", "ETH", ...]
            #   - lista de dicts:   [{"coin": "BTC", "coinName": "Bitcoin"}, ...]
            if isinstance(item, str):
                coin = item.upper()
                name = coin
            else:
                coin = (item.get("coin") or item.get("symbol") or item.get("ticker") or "").upper()
                name = item.get("coinName") or item.get("name") or coin
            if coin:
                result.append(TickerSuggestion(ticker=coin, name=name, type="cripto"))
        return result

    if asset_type in ("stock_int", "etf_int"):
        yf_type = "stock" if asset_type == "stock_int" else "etf"
        raw = await _yf_search_async(q.strip(), limit, yf_type)
        return [
            TickerSuggestion(ticker=item["ticker"], name=item["name"], type=item.get("type"))
            for item in raw
        ]

    raw = await fetch_ticker_suggestions(q.strip(), limit, asset_type)
    result = []
    for item in raw:
        ticker_val = item.get("stock") or item.get("ticker") or item.get("symbol")
        name = item.get("name") or item.get("longName") or item.get("shortName") or ""
        kind = item.get("type") or item.get("assetType")
        if ticker_val:
            result.append(TickerSuggestion(ticker=ticker_val.upper(), name=name, type=kind))
    return result


@router.get("/tesouro/search", response_model=list[TreasuryItem])
async def search_treasury(
    q: str = Query("", min_length=0),
    _=Depends(get_current_user),
):
    api_items = await fetch_treasury_list()
    raw_list = api_items if api_items else _TESOURO_STATIC
    parsed = [_parse_treasury_item(i) for i in raw_list]
    parsed = [i for i in parsed if i is not None]
    if q.strip():
        q_lower = q.strip().lower()
        parsed = [i for i in parsed if q_lower in i.name.lower() or q_lower in (i.slug or "").lower()]
    return parsed


@router.get("/tesouro/price", response_model=TreasuryPriceResponse)
async def get_treasury_price(
    slug: str = Query(...),
    date: str = Query(...),
    _=Depends(get_current_user),
):
    today = __import__('datetime').date.today().isoformat()
    use_hist = date != today
    price = None

    if use_hist:
        price = await fetch_treasury_price_by_date(slug, date)

    if price is None:
        items = await fetch_treasury_list()
        for item in items:
            item_slug = item.get("slug") or item.get("symbol") or ""
            if item_slug == slug:
                p = item.get("buyPrice") or item.get("basePrice")
                if p:
                    price = float(p)
                break

    return TreasuryPriceResponse(slug=slug, price=price, price_date=date)


@router.get("/quote/{ticker}", response_model=TickerQuoteResponse)
async def get_ticker_quote(
    ticker: str,
    date: Optional[str] = Query(None),
    asset_type: Optional[str] = Query(None, description="Tipo do ativo: CRIPTO, ACAO, FII, etc."),
    _=Depends(get_current_user),
):
    """
    Retorna cotacao de um ticker.

    Para criptos, aceita tanto o codigo (BTC) quanto o nome completo (BITCOIN).
    Se asset_type=CRIPTO ou o ticker for reconhecido como nome de cripto,
    usa o endpoint /api/v2/crypto da BRAPI em vez de /api/v2/quote.
    """
    t = ticker.strip().upper()
    today = __import__('datetime').date.today().isoformat()
    use_hist = date and date != today

    # Tenta resolver como cripto: BITCOIN->BTC, ETH->ETH, BTC-USD->BTC
    crypto_code = _resolve_crypto_ticker(t, db_asset_type=asset_type)

    # Caminho cripto
    if crypto_code:
        prices = await fetch_crypto_quote([crypto_code])
        price = prices.get(crypto_code)
        if price is not None:
            return TickerQuoteResponse(
                ticker=t,
                name=_CRYPTO_NAME_TO_TICKER.get(t, crypto_code),
                price=price,
                currency="BRL",
                asset_type="CRIPTO",
                source="brapi",
                price_date=today,
            )
        # Se a BRAPI falhou para cripto, nao tenta BRAPI /quote (vai retornar 404)
        raise HTTPException(
            status_code=404,
            detail=f"Cotacao cripto nao encontrada para '{t}' (codigo: {crypto_code})."
        )

    # Caminho normal (B3, stocks, ETF, etc.)
    if use_hist:
        hist_price = await fetch_historical_price(t, date)
        if hist_price:
            return TickerQuoteResponse(
                ticker=t, price=hist_price, currency="BRL",
                source="brapi", price_date=date,
            )

    info = await fetch_asset_info(t)
    if info and info.get("regularMarketPrice"):
        return TickerQuoteResponse(
            ticker=t,
            name=info.get("longName") or info.get("shortName"),
            price=float(info["regularMarketPrice"]),
            currency=(info.get("currency") or "BRL").upper(),
            asset_type=_detect_type_from_brapi(info),
            source="brapi",
            price_date=today,
        )

    yf_info = await _yf_fetch_async(t, date if use_hist else None)
    if yf_info and yf_info.get("price"):
        return TickerQuoteResponse(
            ticker=t,
            name=yf_info.get("name"),
            price=yf_info["price"],
            currency=yf_info.get("currency", "USD"),
            asset_type=yf_info.get("asset_type"),
            source="yfinance",
            price_date=date or today,
        )

    raise HTTPException(status_code=404, detail=f"Ticker '{t}' nao encontrado.")


@router.get("/csv-template", tags=["csv-import"])
async def get_csv_template():
    """
    Retorna um template CSV para importacao de transacoes.
    Download como arquivo CSV.
    """
    csv_content = csv_import_service.generate_csv_template()
    return FileResponse(
        io.BytesIO(csv_content.encode()),
        media_type="text/csv",
        filename="portfolio_import_template.csv"
    )
