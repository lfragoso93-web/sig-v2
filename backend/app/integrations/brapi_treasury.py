"""
Integração BRAPI — Tesouro Direto.

Fluxo primário:
- GET /api/v2/treasury/list
- GET /api/v2/treasury/indicators
- GET /api/v2/treasury/indicators/history

Fallbacks:
- Tesouro Transparente/CKAN, quando disponível.
- Lista sintética para produtos de longo prazo que a BRAPI pode não listar,
  especialmente Tesouro RendA+ Aposentadoria Extra e Tesouro Educa+.

Os títulos usam `symbol` em formato slug minúsculo, ex.:
`tesouro-selic-01032031` e `tesouro-renda-mais-2060`.
"""
from __future__ import annotations

import csv
import io
import logging
import re
import unicodedata
from datetime import date, datetime, timezone
from typing import Iterable, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

BRAPI_TREASURY_BASE = "https://brapi.dev/api/v2/treasury"
BRAPI_TREASURY_CHUNK = 20

TESOURO_TRANSPARENTE_PACKAGE = (
    "https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show"
)
TESOURO_TRANSPARENTE_DATASET_ID = (
    "precos-e-taxas-dos-titulos-publicos-ofertados-no-tesouro-direto"
)

_SYNTHETIC_LONG_TERM_BONDS: list[dict] = [
    *[
        {
            "symbol": f"tesouro-renda-mais-{year}",
            "bondType": "Tesouro RendA+ Aposentadoria Extra",
            "name": f"Tesouro RendA+ Aposentadoria Extra {year}",
            "maturityYear": year,
            "indexer": "IPCA",
            "couponType": "monthly_income",
            "source": "synthetic_treasury_long_term",
        }
        for year in range(2030, 2070, 5)
    ],
    *[
        {
            "symbol": f"tesouro-educa-mais-{year}",
            "bondType": "Tesouro Educa+",
            "name": f"Tesouro Educa+ {year}",
            "maturityYear": year,
            "indexer": "IPCA",
            "couponType": "monthly_income",
            "source": "synthetic_treasury_long_term",
        }
        for year in range(2026, 2051)
    ],
]

_TREASURY_SYMBOL_RE = re.compile(r"^tesouro-[a-z0-9-]+-\d{4,8}$")


def _auth_headers() -> dict:
    if settings.BRAPI_TOKEN:
        return {"Authorization": f"Bearer {settings.BRAPI_TOKEN}"}
    return {}


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _slug_text(value: str | None) -> str:
    raw = _strip_accents(value or "").lower().replace("+", " mais ")
    raw = re.sub(r"[^a-z0-9]+", "-", raw)
    raw = re.sub(r"-+", "-", raw).strip("-")
    return raw


def _year_from_text(value: str | None) -> Optional[int]:
    match = re.search(r"20\d{2}", value or "")
    return int(match.group(0)) if match else None


def canonical_treasury_symbol_from_text(value: str | None) -> Optional[str]:
    """Converte nomes públicos comuns para symbol canônico usado pelo SGI."""
    if not value:
        return None
    slug = _slug_text(value)
    year = _year_from_text(value)
    if not year:
        return None

    if "renda" in slug:
        return f"tesouro-renda-mais-{year}"
    if "educa" in slug:
        return f"tesouro-educa-mais-{year}"
    return None


def is_brapi_treasury_symbol(value: str | None) -> bool:
    """True somente para slugs que vale a pena enviar para /treasury/indicators."""
    raw = (value or "").strip().lower()
    if not raw or " " in raw or "+" in raw:
        return False
    return bool(_TREASURY_SYMBOL_RE.match(raw))


def _items_from_payload(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []

    for key in (
        "results",
        "treasury",
        "treasuries",
        "bonds",
        "items",
        "data",
        "list",
    ):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    maybe_values = [v for v in payload.values() if isinstance(v, dict)]
    if maybe_values:
        return maybe_values
    return []


def _symbol_from_item(item: dict) -> str:
    symbol = str(
        item.get("symbol")
        or item.get("slug")
        or item.get("ticker")
        or item.get("id")
        or ""
    ).strip().lower()
    if symbol:
        return symbol
    return canonical_treasury_symbol_from_text(
        str(item.get("name") or item.get("bondType") or item.get("Tipo Titulo") or "")
        + " "
        + str(item.get("maturityYear") or item.get("Data Vencimento") or "")
    ) or ""


def _price_from_item(item: dict) -> Optional[float]:
    for field in (
        "buyPrice",
        "basePrice",
        "sellPrice",
        "price",
        "unitPrice",
        "valorUnitario",
        "PU Compra Manha",
        "PU Venda Manha",
        "PU Base Manha",
        "PU Compra Tarde",
        "PU Venda Tarde",
        "PU Base Tarde",
    ):
        value = item.get(field)
        if value is None:
            continue
        try:
            parsed = float(str(value).replace(".", "").replace(",", ".") if isinstance(value, str) else value)
            if parsed > 0:
                return parsed
        except (TypeError, ValueError):
            continue
    return None


def _history_date(value: object) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)

    raw = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(raw[:10], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    try:
        dt = datetime.fromisoformat(raw[:10])
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


async def _fetch_brapi_treasury_list(
    client: httpx.AsyncClient,
    indexer: Optional[str] = None,
    coupon_type: Optional[str] = None,
) -> list[dict]:
    params: dict[str, str] = {}
    if indexer:
        params["indexer"] = indexer.lower()
    if coupon_type:
        params["couponType"] = coupon_type.lower()

    response = await client.get(
        f"{BRAPI_TREASURY_BASE}/list",
        headers=_auth_headers(),
        params=params,
    )
    response.raise_for_status()
    items = _items_from_payload(response.json())
    logger.info("[treasury] BRAPI list retornou %d títulos", len(items))
    return items


def _resource_candidates(payload: dict) -> list[str]:
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


def _parse_tesouro_csv(text: str) -> list[dict]:
    sample = text[:4096]
    delimiter = ";" if sample.count(";") >= sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    items: list[dict] = []
    seen: set[str] = set()
    for row in reader:
        title = (
            row.get("Tipo Titulo")
            or row.get("Tipo Título")
            or row.get("Titulo")
            or row.get("Título")
            or row.get("Nome")
            or ""
        )
        maturity = row.get("Data Vencimento") or row.get("Vencimento") or ""
        year = _year_from_text(maturity) or _year_from_text(title)
        symbol = canonical_treasury_symbol_from_text(f"{title} {year or ''}")
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        items.append(
            {
                "symbol": symbol,
                "bondType": title.strip() or symbol,
                "name": f"{title.strip()} {year}" if year else title.strip() or symbol,
                "maturityYear": year,
                "maturityDate": maturity,
                "indexer": "IPCA" if symbol.startswith(("tesouro-renda-mais", "tesouro-educa-mais")) else None,
                "source": "tesouro_transparente_csv",
            }
        )
    return items


async def _fetch_tesouro_transparente_list(client: httpx.AsyncClient) -> list[dict]:
    try:
        resp = await client.get(
            TESOURO_TRANSPARENTE_PACKAGE,
            params={"id": TESOURO_TRANSPARENTE_DATASET_ID},
            timeout=20.0,
        )
        resp.raise_for_status()
        urls = _resource_candidates(resp.json())
    except Exception as exc:
        logger.info("[treasury] Tesouro Transparente indisponível para catálogo: %s", exc)
        return []

    for url in urls[:3]:
        try:
            csv_resp = await client.get(url, timeout=45.0)
            csv_resp.raise_for_status()
            items = _parse_tesouro_csv(csv_resp.text)
            if items:
                logger.info("[treasury] Tesouro Transparente retornou %d títulos", len(items))
                return items
        except Exception as exc:
            logger.info("[treasury] falha ao ler recurso Tesouro Transparente %s: %s", url, exc)
    return []


def _merge_items(*groups: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for group in groups:
        for item in group:
            symbol = _symbol_from_item(item)
            if not symbol:
                continue
            current = dict(item)
            current["symbol"] = symbol
            if symbol not in merged:
                merged[symbol] = current
            else:
                for key, value in current.items():
                    if value and not merged[symbol].get(key):
                        merged[symbol][key] = value
    return list(merged.values())


async def fetch_treasury_list(
    indexer: Optional[str] = None,
    coupon_type: Optional[str] = None,
) -> list[dict]:
    """Lista títulos disponíveis do Tesouro Direto com fallback para RendA+/Educa+."""
    brapi_items: list[dict] = []
    transparente_items: list[dict] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            brapi_items = await _fetch_brapi_treasury_list(client, indexer=indexer, coupon_type=coupon_type)
        except Exception as exc:
            logger.warning("[treasury] BRAPI list falhou: %s", exc)

        if not indexer and not coupon_type:
            transparente_items = await _fetch_tesouro_transparente_list(client)

    items = _merge_items(brapi_items, transparente_items, _SYNTHETIC_LONG_TERM_BONDS)
    logger.info(
        "[treasury] catálogo consolidado: %d títulos (brapi=%d, transparente=%d, fallback=%d)",
        len(items),
        len(brapi_items),
        len(transparente_items),
        len(_SYNTHETIC_LONG_TERM_BONDS),
    )
    return items


async def _request_treasury_indicators(
    client: httpx.AsyncClient,
    symbols: list[str],
) -> list[dict]:
    response = await client.get(
        f"{BRAPI_TREASURY_BASE}/indicators",
        headers=_auth_headers(),
        params={"symbols": ",".join(symbols)},
    )
    response.raise_for_status()
    return _items_from_payload(response.json())


async def fetch_treasury_indicators(symbols: Iterable[str]) -> dict[str, dict]:
    """Consulta indicadores atuais por symbol canônico da BRAPI."""
    selected = []
    skipped = 0
    seen: set[str] = set()
    for raw in symbols:
        raw_symbol = str(raw or "").strip().lower()
        symbol = raw_symbol if is_brapi_treasury_symbol(raw_symbol) else canonical_treasury_symbol_from_text(raw_symbol)
        if not symbol or not is_brapi_treasury_symbol(symbol):
            skipped += 1
            continue
        if symbol not in seen:
            seen.add(symbol)
            selected.append(symbol)

    if skipped:
        logger.info("[treasury] %d símbolos não-canônicos ignorados em indicators", skipped)
    if not selected:
        return {}

    result: dict[str, dict] = {}
    invalid: list[str] = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i in range(0, len(selected), BRAPI_TREASURY_CHUNK):
            chunk = selected[i:i + BRAPI_TREASURY_CHUNK]
            try:
                items = await _request_treasury_indicators(client, chunk)
            except Exception as exc:
                logger.info(
                    "[treasury] indicators em lote falhou para %d símbolos; tentando individualmente: %s",
                    len(chunk),
                    exc,
                )
                for symbol in chunk:
                    try:
                        items = await _request_treasury_indicators(client, [symbol])
                    except Exception:
                        invalid.append(symbol)
                        continue
                    for item in items:
                        returned_symbol = _symbol_from_item(item)
                        if returned_symbol:
                            result[returned_symbol] = item
                continue

            for item in items:
                returned_symbol = _symbol_from_item(item)
                if returned_symbol:
                    result[returned_symbol] = item

    if invalid:
        logger.info("[treasury] %d symbols sem indicators na BRAPI: %s", len(invalid), invalid[:10])
    return result


async def fetch_treasury_prices(symbols: Iterable[str]) -> dict[str, float]:
    """Retorna preço unitário atual por symbol canônico."""
    indicators = await fetch_treasury_indicators(symbols)
    prices: dict[str, float] = {}
    for symbol, item in indicators.items():
        price = _price_from_item(item)
        if price is not None:
            prices[symbol] = price
    return prices


async def fetch_treasury_history(
    symbols: Iterable[str],
    start_date: date,
    end_date: date,
) -> dict[str, list[tuple[datetime, float]]]:
    """Busca histórico diário de preços unitários para títulos do Tesouro."""
    selected = [s.strip().lower() for s in symbols if is_brapi_treasury_symbol(s)]
    if not selected:
        return {}

    output: dict[str, list[tuple[datetime, float]]] = {s: [] for s in selected}
    async with httpx.AsyncClient(timeout=60.0) as client:
        for i in range(0, len(selected), BRAPI_TREASURY_CHUNK):
            chunk = selected[i:i + BRAPI_TREASURY_CHUNK]
            try:
                response = await client.get(
                    f"{BRAPI_TREASURY_BASE}/indicators/history",
                    headers=_auth_headers(),
                    params={
                        "symbols": ",".join(chunk),
                        "startDate": start_date.isoformat(),
                        "endDate": end_date.isoformat(),
                    },
                )
                response.raise_for_status()
                items = _items_from_payload(response.json())
            except Exception as exc:
                logger.info("[treasury] history em lote falhou para %d símbolos; tentando individualmente: %s", len(chunk), exc)
                items = []
                for symbol in chunk:
                    try:
                        response = await client.get(
                            f"{BRAPI_TREASURY_BASE}/indicators/history",
                            headers=_auth_headers(),
                            params={
                                "symbols": symbol,
                                "startDate": start_date.isoformat(),
                                "endDate": end_date.isoformat(),
                            },
                        )
                        response.raise_for_status()
                        items.extend(_items_from_payload(response.json()))
                    except Exception:
                        continue

            for item in items:
                symbol = _symbol_from_item(item)
                if not symbol:
                    continue
                raw_history = (
                    item.get("historicalDataPrice")
                    or item.get("history")
                    or item.get("data")
                    or item.get("prices")
                    or []
                )
                rows: list[tuple[datetime, float]] = []
                if isinstance(raw_history, list):
                    for row in raw_history:
                        if not isinstance(row, dict):
                            continue
                        dt = _history_date(row.get("date") or row.get("timestamp"))
                        price = _price_from_item(row)
                        if dt and price is not None:
                            rows.append((dt, price))
                rows.sort(key=lambda x: x[0])
                output[symbol] = rows

    return output
