from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import Response
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel
import asyncio
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
    fetch_quote,
    fetch_logo,
    fetch_treasury_bonds,
)
from app.integrations.yfinance_client import fetch_yfinance_info

logger = logging.getLogger(__name__)

router = APIRouter(tags=["assets"])


class AssetSearchResult(BaseModel):
    ticker: str
    name: str | None = None
    asset_type: str | None = None
    exchange: str | None = None
    currency: str | None = None
    current_price: float | None = None
    logo_url: str | None = None
    source: str | None = None


@router.get("/", response_model=list[AssetResponse])
async def list_assets(
    q: str | None = Query(default=None, description="Filtro por ticker ou nome"),
    asset_type: AssetType | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await search_assets(db, q=q, asset_type=asset_type)


@router.post("/", response_model=AssetResponse, status_code=201)
async def create_asset(
    data: AssetCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await get_or_create_asset(db, data)


@router.get("/search", response_model=list[AssetSearchResult])
async def search_asset_ticker(
    q: str = Query(..., min_length=2, description="Ticker ou termo de busca"),
    asset_type: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Busca ativo por ticker em fontes internas e provedores de mercado."""
    term = q.strip().upper()
    requested_type = asset_type.upper() if asset_type else None

    local = await db.execute(
        select(Asset).where(
            or_(
                func.upper(Asset.ticker).like(f"%{term}%"),
                func.upper(func.coalesce(Asset.name, "")).like(f"%{term}%"),
            )
        ).limit(10)
    )
    local_assets = list(local.scalars().all())
    if local_assets:
        return [
            AssetSearchResult(
                ticker=a.ticker,
                name=a.name,
                asset_type=a.asset_type.value if hasattr(a.asset_type, "value") else str(a.asset_type),
                exchange=a.exchange,
                currency=a.currency,
                current_price=a.current_price,
                logo_url=a.logo_url,
                source="internal",
            )
            for a in local_assets
        ]

    def _looks_like_ticker(value: str) -> bool:
        return value.replace(".", "").replace("-", "").isalnum() and len(value) <= 12

    candidates: list[AssetSearchResult] = []
    if requested_type in {"ACAO", "FII", "ETF_NACIONAL", "BDR"} or (requested_type is None and _looks_like_ticker(term)):
        try:
            info = await fetch_asset_info(term)
            quote = await fetch_quote(term)
            logo_url = await fetch_logo(term)
            candidates.append(
                AssetSearchResult(
                    ticker=info.get("ticker") or term,
                    name=info.get("name"),
                    asset_type=info.get("asset_type"),
                    exchange=info.get("exchange"),
                    currency=info.get("currency", "BRL"),
                    current_price=quote.get("price") if quote else None,
                    logo_url=logo_url,
                    source="market_provider",
                )
            )
        except Exception as exc:
            logger.info("Busca provedor nacional falhou para %s: %s", term, exc)

    if requested_type in {"STOCK", "ETF_INTERNACIONAL"} or (requested_type is None and not candidates):
        try:
            info = await fetch_yfinance_info(term)
            candidates.append(
                AssetSearchResult(
                    ticker=info.get("ticker") or term,
                    name=info.get("name"),
                    asset_type=info.get("asset_type"),
                    exchange=info.get("exchange"),
                    currency=info.get("currency", "USD"),
                    current_price=info.get("current_price"),
                    logo_url=info.get("logo_url"),
                    source="market_provider",
                )
            )
        except Exception as exc:
            logger.info("Busca provedor internacional falhou para %s: %s", term, exc)

    if requested_type in {"TESOURO_DIRETO", "TESOURO"}:
        try:
            bonds = await fetch_treasury_bonds()
            matches = [b for b in bonds if term in str(b.get("ticker", "")).upper() or term in str(b.get("name", "")).upper()]
            candidates.extend(
                AssetSearchResult(
                    ticker=b.get("ticker"),
                    name=b.get("name"),
                    asset_type="TESOURO_DIRETO",
                    exchange="Tesouro Nacional",
                    currency="BRL",
                    current_price=b.get("unit_price"),
                    source="market_provider",
                )
                for b in matches[:10]
            )
        except Exception as exc:
            logger.info("Busca Tesouro Direto falhou para %s: %s", term, exc)

    return candidates[:10]


@router.get("/{ticker}/price")
async def asset_price(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await get_current_price(db, ticker)


@router.get("/{ticker}/history")
async def asset_history(
    ticker: str,
    days: int = Query(default=365, ge=1, le=3650),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await get_price_history(db, ticker, days=days)


@router.get("/brapi/search", response_model=list[AssetSearchResult])
async def brapi_search(
    q: str = Query(..., min_length=2, description="Ticker ou termo"),
    asset_type: str | None = Query(default=None),
    current_user=Depends(get_current_user),
):
    term = q.strip().upper()
    t = term
    if asset_type:
        asset_type = asset_type.upper()

    if asset_type in {"ACAO", "FII", "ETF_NACIONAL", "BDR"}:
        info = await fetch_asset_info(t)
        quote = await fetch_quote(t)
        logo_url = await fetch_logo(t)
        return [AssetSearchResult(
            ticker=info.get("ticker") or t,
            name=info.get("name"),
            exchange=info.get("exchange"),
            currency=info.get("currency", "BRL"),
            asset_type=info.get("asset_type"),
            current_price=quote.get("price") if quote else None,
            logo_url=logo_url,
            source="market_provider",
        )]

    if asset_type in {"TESOURO_DIRETO", "TESOURO"}:
        bonds = await fetch_treasury_bonds()
        matches = [b for b in bonds if t in str(b.get("ticker", "")).upper() or t in str(b.get("name", "")).upper()]
        return [AssetSearchResult(
            ticker=b.get("ticker"),
            name=b.get("name"),
            exchange="Tesouro Nacional",
            currency="BRL",
            asset_type="TESOURO_DIRETO",
            current_price=b.get("unit_price"),
            source="market_provider",
        ) for b in matches[:10]]

    if asset_type in {"STOCK", "ETF_INTERNACIONAL"}:
        yf_info = await fetch_yfinance_info(t)
        return [AssetSearchResult(
            ticker=yf_info.get("ticker") or t,
            name=yf_info.get("name"),
            exchange=yf_info.get("exchange"),
            currency=yf_info.get("currency", "USD"),
            asset_type=yf_info.get("asset_type"),
            source="market_provider",
            current_price=yf_info.get("current_price"),
            logo_url=yf_info.get("logo_url"),
        )]

    raise HTTPException(status_code=404, detail=f"Ticker '{t}' nao encontrado.")


@router.get("/csv-template", tags=["csv-import"])
async def get_csv_template():
    """
    Retorna um modelo CSV aceito pela importacao de transacoes.
    O arquivo possui cabecalho obrigatorio e exemplos em formato importavel.
    """
    csv_content = csv_import_service.generate_csv_template()
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="portfolio_import_template.csv"',
        },
    )
