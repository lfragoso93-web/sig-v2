"""Cliente do Tesouro Transparente/CKAN para preços históricos do Tesouro Direto.

A fonte oficial é consultada antes da BRAPI. O cliente descobre recursos CSV do
conjunto público de preços e taxas, normaliza nomes/vencimentos para o símbolo
canônico do SGI e devolve séries diárias por título.
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Iterable

import httpx

from app.integrations.brapi_treasury import canonical_treasury_symbol_from_text

logger = logging.getLogger(__name__)

_PACKAGE_ENDPOINTS = (
    "https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show",
    "https://tesourotransparente.gov.br/ckan/api/3/action/package_show",
)
_DATASET_IDS = (
    "precos-e-taxas-dos-titulos-publicos-ofertados-no-tesouro-direto",
    "taxas-dos-titulos-ofertados-pelo-tesouro-direto",
)


def _resource_urls(payload: object) -> list[str]:
    if not isinstance(payload, dict):
        return []
    resources = ((payload.get("result") or {}).get("resources") or [])
    urls: list[str] = []
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        fmt = str(resource.get("format") or "").lower()
        url = str(resource.get("url") or resource.get("download_url") or "").strip()
        if not url:
            continue
        if "csv" in fmt or ".csv" in url.lower():
            urls.append(url)
    return urls


async def discover_csv_resources(client: httpx.AsyncClient) -> list[str]:
    """Descobre recursos CSV oficiais, tolerando variações de host e slug."""
    for endpoint in _PACKAGE_ENDPOINTS:
        for dataset_id in _DATASET_IDS:
            try:
                response = await client.get(endpoint, params={"id": dataset_id}, timeout=25.0)
                response.raise_for_status()
                urls = _resource_urls(response.json())
                if urls:
                    logger.info(
                        "[tesouro_transparente] dataset=%s recursos_csv=%d",
                        dataset_id,
                        len(urls),
                    )
                    return urls
            except Exception as exc:
                logger.info(
                    "[tesouro_transparente] package_show indisponivel endpoint=%s dataset=%s erro=%s",
                    endpoint,
                    dataset_id,
                    exc,
                )
    return []


def _first(row: dict[str, str], *names: str) -> str:
    normalized = {str(key).strip().lower(): value for key, value in row.items()}
    for name in names:
        value = normalized.get(name.strip().lower())
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _parse_date(value: str) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.strptime(raw[:10], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _parse_decimal(value: str) -> float | None:
    raw = (value or "").strip().replace("R$", "").replace(" ", "")
    if not raw:
        return None
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    try:
        parsed = Decimal(raw)
    except InvalidOperation:
        return None
    return float(parsed) if parsed > 0 else None


def parse_history_csv(
    text: str,
    symbols: Iterable[str] | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, list[tuple[datetime, float]]]:
    """Converte um recurso CSV oficial em séries diárias por símbolo canônico."""
    sample = text[:8192]
    delimiter = ";" if sample.count(";") >= sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    selected = {str(symbol).strip().lower() for symbol in symbols or [] if symbol}
    output: dict[str, dict[datetime, float]] = {}

    for row in reader:
        title = _first(row, "Tipo Titulo", "Tipo Título", "Titulo", "Título", "Nome")
        maturity = _first(row, "Data Vencimento", "Vencimento")
        symbol = canonical_treasury_symbol_from_text(f"{title} {maturity}")
        if not symbol:
            continue
        symbol = symbol.lower()
        if selected and symbol not in selected:
            continue

        dt = _parse_date(_first(row, "Data Base", "Data", "Data Referencia", "Data Referência"))
        if dt is None:
            continue
        day = dt.date()
        if start_date and day < start_date:
            continue
        if end_date and day > end_date:
            continue

        price = None
        for field in (
            "PU Compra Manha",
            "PU Compra Manhã",
            "PU Base Manha",
            "PU Base Manhã",
            "PU Venda Manha",
            "PU Venda Manhã",
            "PU Compra Tarde",
            "PU Base Tarde",
            "PU Venda Tarde",
            "Preco Unitario",
            "Preço Unitário",
        ):
            price = _parse_decimal(_first(row, field))
            if price is not None:
                break
        if price is None:
            continue
        output.setdefault(symbol, {})[dt] = price

    return {
        symbol: sorted(rows.items(), key=lambda item: item[0])
        for symbol, rows in output.items()
    }


async def fetch_official_treasury_history(
    symbols: Iterable[str],
    start_date: date,
    end_date: date,
) -> dict[str, list[tuple[datetime, float]]]:
    """Busca histórico oficial do Tesouro Transparente para os símbolos pedidos."""
    selected = sorted({str(symbol).strip().lower() for symbol in symbols if symbol})
    output: dict[str, list[tuple[datetime, float]]] = {symbol: [] for symbol in selected}
    if not selected:
        return output

    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        resources = await discover_csv_resources(client)
        for url in resources:
            try:
                response = await client.get(url, timeout=90.0)
                response.raise_for_status()
                parsed = parse_history_csv(
                    response.text,
                    symbols=selected,
                    start_date=start_date,
                    end_date=end_date,
                )
            except Exception as exc:
                logger.info("[tesouro_transparente] falha ao ler recurso=%s erro=%s", url, exc)
                continue

            for symbol, rows in parsed.items():
                if rows:
                    output[symbol] = rows
            if all(output.get(symbol) for symbol in selected):
                break

    covered = sum(1 for rows in output.values() if rows)
    logger.info(
        "[tesouro_transparente] historico concluido requested=%d covered=%d",
        len(selected),
        covered,
    )
    return output
