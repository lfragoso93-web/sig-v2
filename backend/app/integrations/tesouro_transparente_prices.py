"""Fallback de preços atuais do Tesouro Direto via Tesouro Transparente.

Usado quando a BRAPI lista/reconhece o título, mas não devolve indicador de preço,
caso comum em alguns vencimentos de Tesouro RendA+ e Educa+.
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import date, datetime
from typing import Iterable, Optional

import httpx

from app.integrations.brapi_treasury import canonical_treasury_symbol_from_text

logger = logging.getLogger(__name__)

_PACKAGE_URL = "https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show"
_DATASET_ID = "precos-e-taxas-dos-titulos-publicos-ofertados-no-tesouro-direto"

_TITLE_FIELDS = ("Tipo Titulo", "Tipo Título", "Titulo", "Título", "Nome")
_MATURITY_FIELDS = ("Data Vencimento", "Vencimento")
_DATE_FIELDS = ("Data Base", "Data", "data", "date")
_PRICE_FIELDS = (
    "PU Compra Manha",
    "PU Compra Manhã",
    "PU Compra Tarde",
    "PU Venda Manha",
    "PU Venda Manhã",
    "PU Venda Tarde",
    "PU Base Manha",
    "PU Base Manhã",
    "PU Base Tarde",
    "Valor Unitario",
    "Valor Unitário",
)


def _first(row: dict, fields: tuple[str, ...]) -> str:
    for field in fields:
        value = row.get(field)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _parse_date(value: str) -> Optional[date]:
    raw = (value or "").strip()
    if not raw:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.strptime(raw[:10], fmt).date()
        except ValueError:
            continue
    return None


def _parse_number(value: object) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        if isinstance(value, (int, float)):
            parsed = float(value)
        else:
            raw = str(value).strip().replace("R$", "").replace(" ", "")
            if "," in raw:
                raw = raw.replace(".", "").replace(",", ".")
            parsed = float(raw)
        return parsed if parsed > 0 else None
    except (TypeError, ValueError):
        return None


def _resource_urls(payload: dict) -> list[str]:
    resources = (((payload or {}).get("result") or {}).get("resources") or [])
    urls: list[str] = []
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        fmt = str(resource.get("format") or "").lower()
        url = str(resource.get("url") or resource.get("download_url") or "")
        if url and ("csv" in fmt or url.lower().endswith(".csv")):
            urls.append(url)
    return urls


def _parse_latest_prices(text: str, wanted: set[str]) -> dict[str, tuple[date, float]]:
    sample = text[:4096]
    delimiter = ";" if sample.count(";") >= sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    latest: dict[str, tuple[date, float]] = {}

    for row in reader:
        title = _first(row, _TITLE_FIELDS)
        maturity = _first(row, _MATURITY_FIELDS)
        symbol = canonical_treasury_symbol_from_text(f"{title} {maturity}")
        if not symbol or symbol not in wanted:
            continue

        row_date = _parse_date(_first(row, _DATE_FIELDS)) or date.min
        price = None
        for field in _PRICE_FIELDS:
            price = _parse_number(row.get(field))
            if price is not None:
                break
        if price is None:
            continue

        current = latest.get(symbol)
        if current is None or row_date >= current[0]:
            latest[symbol] = (row_date, price)

    return latest


async def fetch_tesouro_transparente_prices(symbols: Iterable[str]) -> dict[str, float]:
    """Retorna o preço mais recente disponível para os symbols solicitados."""
    wanted = {str(symbol).strip().lower() for symbol in symbols if symbol}
    if not wanted:
        return {}

    async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
        try:
            package = await client.get(_PACKAGE_URL, params={"id": _DATASET_ID})
            package.raise_for_status()
            urls = _resource_urls(package.json())
        except Exception as exc:
            logger.info("[treasury_transparente] catálogo de recursos indisponível: %s", exc)
            return {}

        consolidated: dict[str, tuple[date, float]] = {}
        for url in urls[:5]:
            try:
                response = await client.get(url)
                response.raise_for_status()
                found = _parse_latest_prices(response.text, wanted)
            except Exception as exc:
                logger.debug("[treasury_transparente] recurso indisponível %s: %s", url, exc)
                continue

            for symbol, row in found.items():
                current = consolidated.get(symbol)
                if current is None or row[0] >= current[0]:
                    consolidated[symbol] = row

            if wanted.issubset(consolidated.keys()):
                break

    prices = {symbol: price for symbol, (_, price) in consolidated.items()}
    if prices:
        logger.info("[treasury_transparente] fallback retornou preço para %d título(s)", len(prices))
    return prices
