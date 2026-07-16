"""Leitura anual do arquivo oficial B3 COTAHIST para ativos brasileiros.

Suporta consulta pontual por ticker e leitura em lote por ano. A leitura em lote é
usada pelo B3 Historical Market Rebuild para baixar cada arquivo anual uma única vez.
"""
from __future__ import annotations

import io
import logging
import zipfile
from datetime import datetime, timezone
from typing import Iterable

import httpx

logger = logging.getLogger(__name__)

_URLS = (
    "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{year}.ZIP",
    "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{year}.zip",
)
_VALID_MARKETS = {"010", "020"}


def _parse_record_fields(line: str) -> tuple[str, datetime, float, str] | None:
    if len(line) < 245 or line[:2] != "01":
        return None
    market_type = line[24:27]
    if market_type not in _VALID_MARKETS:
        return None
    symbol = line[12:24].strip().upper()
    raw_date = line[2:10]
    raw_close = line[108:121]
    try:
        timestamp = datetime.strptime(raw_date, "%Y%m%d").replace(tzinfo=timezone.utc)
        close = int(raw_close) / 100.0
    except (TypeError, ValueError):
        return None
    if not symbol or close <= 0:
        return None
    return symbol, timestamp, close, market_type


def _parse_record(line: str, ticker: str) -> tuple[datetime, float] | None:
    parsed = _parse_record_fields(line)
    if parsed is None:
        return None
    symbol, timestamp, close, _market_type = parsed
    if symbol != ticker.upper():
        return None
    return timestamp, close


async def _download_year(year: int) -> bytes | None:
    timeout = httpx.Timeout(90.0, connect=25.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for template in _URLS:
            url = template.format(year=year)
            try:
                response = await client.get(url)
                if response.status_code == 200 and response.content:
                    return response.content
            except Exception as exc:
                logger.info("[b3_cotahist] falha ano=%s url=%s erro=%s", year, url, exc)
    logger.info("[b3_cotahist] arquivo indisponível ano=%s", year)
    return None


def _parse_zip_bulk(
    payload: bytes,
    requested: set[str] | None,
) -> dict[str, list[tuple[datetime, float]]]:
    rows_by_ticker: dict[str, dict[datetime, tuple[float, str]]] = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".txt")]
        if not names:
            return {}
        with archive.open(names[0]) as raw:
            for binary_line in raw:
                line = binary_line.decode("latin-1", errors="ignore").rstrip("\r\n")
                parsed = _parse_record_fields(line)
                if parsed is None:
                    continue
                symbol, timestamp, close, market_type = parsed
                if requested is not None and symbol not in requested:
                    continue
                ticker_rows = rows_by_ticker.setdefault(symbol, {})
                previous = ticker_rows.get(timestamp)
                # Mercado à vista prevalece sobre fracionário quando ambos existirem.
                if previous is None or (previous[1] == "020" and market_type == "010"):
                    ticker_rows[timestamp] = (close, market_type)
    return {
        ticker: sorted(((ts, value[0]) for ts, value in values.items()), key=lambda item: item[0])
        for ticker, values in rows_by_ticker.items()
    }


async def fetch_b3_cotahist_year_bulk(
    year: int,
    tickers: Iterable[str] | None = None,
) -> dict[str, list[tuple[datetime, float]]]:
    """Baixa um arquivo anual uma única vez e retorna séries por ticker."""
    payload = await _download_year(year)
    if not payload:
        return {}
    requested = {str(item).upper().strip() for item in tickers} if tickers is not None else None
    try:
        return _parse_zip_bulk(payload, requested)
    except Exception as exc:
        logger.warning("[b3_cotahist] parse em lote falhou ano=%s erro=%s", year, exc)
        return {}


async def fetch_b3_cotahist(
    ticker: str,
    start_year: int,
    end_year: int,
) -> list[tuple[datetime, float]]:
    """Busca fechamentos anuais oficiais da B3 para um ticker."""
    rows_by_date: dict[datetime, float] = {}
    for year in range(start_year, end_year + 1):
        series = await fetch_b3_cotahist_year_bulk(year, [ticker])
        for timestamp, close in series.get(ticker.upper(), []):
            rows_by_date[timestamp] = close
    return sorted(rows_by_date.items(), key=lambda item: item[0])
