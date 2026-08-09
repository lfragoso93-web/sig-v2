"""Provider canônico do catálogo do Tesouro Direto.

Tesouro Transparente é a fonte primária para o universo histórico. BRAPI é
consultada somente como fallback operacional quando a fonte oficial não produz
um catálogo utilizável. Entradas sintéticas não participam deste contrato.
"""
from __future__ import annotations

import csv
import io
import logging
from typing import Any

import httpx

from app.integrations.brapi_treasury import _fetch_brapi_treasury_list
from app.integrations.tesouro_transparente import (
    _canonical_symbol,
    _first,
    _normalize,
    _parse_date,
    discover_csv_resources,
)

logger = logging.getLogger(__name__)

OFFICIAL_SOURCE = "tesouro_transparente_csv"
BRAPI_FALLBACK_SOURCE = "brapi_fallback"


def _metadata(title: str) -> tuple[str | None, str | None]:
    normalized = _normalize(title)
    if "selic" in normalized:
        indexer = "SELIC"
    elif "ipca" in normalized or "renda" in normalized or "educa" in normalized:
        indexer = "IPCA"
    elif "igp m" in normalized or "igpm" in normalized:
        indexer = "IGPM"
    elif "prefixado" in normalized:
        indexer = "PREFIXADO"
    else:
        indexer = None

    if "renda" in normalized or "educa" in normalized:
        coupon = "monthly_income"
    elif "juros semestrais" in normalized:
        coupon = "semestral"
    else:
        coupon = "zero"
    return indexer, coupon


def parse_official_catalog_csv(text: str) -> list[dict[str, Any]]:
    """Extrai identidades únicas de títulos do histórico oficial diário."""
    sample = text[:8192]
    delimiter = ";" if sample.count(";") >= sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    catalog: dict[str, dict[str, Any]] = {}

    for row in reader:
        title = _first(row, "Tipo Titulo", "Tipo Título", "Titulo", "Título", "Nome")
        maturity = _first(row, "Data Vencimento", "Vencimento")
        symbol = _canonical_symbol(title, maturity)
        maturity_dt = _parse_date(maturity)
        if not symbol or maturity_dt is None:
            continue

        indexer, coupon = _metadata(title)
        catalog[symbol] = {
            "symbol": symbol,
            "bondType": title,
            "name": f"{title} {maturity_dt.date().isoformat()}",
            "maturityYear": maturity_dt.year,
            "maturityDate": maturity_dt.date().isoformat(),
            "indexer": indexer,
            "couponType": coupon,
            "source": OFFICIAL_SOURCE,
        }

    return list(catalog.values())


async def _fetch_official_catalog(client: httpx.AsyncClient) -> list[dict]:
    resources = await discover_csv_resources(client)
    last_error: Exception | None = None
    for url in resources:
        try:
            response = await client.get(url, timeout=90.0)
            response.raise_for_status()
            items = parse_official_catalog_csv(response.text)
            if items:
                logger.info("[treasury] catálogo oficial retornou %d títulos históricos", len(items))
                return items
        except Exception as exc:
            last_error = exc
            logger.warning("[treasury] recurso oficial de catálogo falhou %s: %s", url, exc)
    if last_error:
        logger.warning("[treasury] catálogo oficial indisponível: %s", last_error)
    return []


async def fetch_treasury_catalog() -> list[dict]:
    """Retorna catálogo histórico oficial; usa BRAPI somente como fallback."""
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        official = await _fetch_official_catalog(client)
        if official:
            return official

        fallback = await _fetch_brapi_treasury_list(client)
        normalized: list[dict] = []
        for item in fallback:
            current = dict(item)
            current.setdefault("source", BRAPI_FALLBACK_SOURCE)
            normalized.append(current)
        logger.warning("[treasury] usando BRAPI como fallback de catálogo: %d títulos", len(normalized))
        return normalized
