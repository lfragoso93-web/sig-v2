"""Leitura anual do arquivo oficial B3 COTAHIST para ativos brasileiros.

Usado como fallback para ativos deslistados ou indisponíveis em BRAPI/Yahoo.
"""
from __future__ import annotations

import io
import logging
import zipfile
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

_URLS = (
    "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{year}.ZIP",
    "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{year}.zip",
)


def _parse_record(line: str, ticker: str) -> tuple[datetime, float] | None:
    if len(line) < 245 or line[:2] != "01":
        return None
    symbol = line[12:24].strip().upper()
    if symbol != ticker.upper():
        return None
    # Tipo de mercado 010 = vista. Aceitamos também fracionário 020 para
    # preservar histórico quando o provedor consolidou o ticker principal.
    market_type = line[24:27]
    if market_type not in {"010", "020"}:
        return None
    raw_date = line[2:10]
    raw_close = line[108:121]
    try:
        timestamp = datetime.strptime(raw_date, "%Y%m%d").replace(tzinfo=timezone.utc)
        close = int(raw_close) / 100.0
    except (TypeError, ValueError):
        return None
    if close <= 0:
        return None
    return timestamp, close


async def fetch_b3_cotahist(
    ticker: str,
    start_year: int,
    end_year: int,
) -> list[tuple[datetime, float]]:
    """Busca fechamentos anuais oficiais da B3 para um ticker."""
    rows_by_date: dict[datetime, float] = {}
    timeout = httpx.Timeout(60.0, connect=20.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for year in range(start_year, end_year + 1):
            payload: bytes | None = None
            for template in _URLS:
                url = template.format(year=year)
                try:
                    response = await client.get(url)
                    if response.status_code == 200 and response.content:
                        payload = response.content
                        break
                except Exception as exc:
                    logger.info("[b3_cotahist] falha ano=%s url=%s erro=%s", year, url, exc)
            if not payload:
                logger.info("[b3_cotahist] arquivo indisponível ano=%s", year)
                continue
            try:
                with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                    names = [name for name in archive.namelist() if name.lower().endswith(".txt")]
                    if not names:
                        continue
                    with archive.open(names[0]) as raw:
                        for binary_line in raw:
                            line = binary_line.decode("latin-1", errors="ignore").rstrip("\r\n")
                            parsed = _parse_record(line, ticker)
                            if parsed:
                                rows_by_date[parsed[0]] = parsed[1]
            except Exception as exc:
                logger.warning("[b3_cotahist] parse falhou ano=%s ticker=%s erro=%s", year, ticker, exc)

    return sorted(rows_by_date.items(), key=lambda item: item[0])
