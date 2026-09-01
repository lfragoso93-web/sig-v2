"""Leitura anual do arquivo oficial B3 COTAHIST para ativos brasileiros.

Suporta consulta pontual por ticker e leitura em lote por ano. A leitura em lote é
usada pelo B3 Historical Market Rebuild para baixar cada arquivo anual uma única vez.
"""
from __future__ import annotations

import io
import logging
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Iterable

import httpx

logger = logging.getLogger(__name__)

_URLS = (
    "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{year}.ZIP",
    "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{year}.zip",
)
_VALID_MARKETS = {"010", "020"}
_CENTS = Decimal("100")
_SUPPORTED_SPOT_MARKETS = {"010", "020"}
_RIGHTS_OR_RECEIPTS_MARKERS = {
    "DIR",
    "DIREITO",
    "REC",
    "RECIBO",
    "SUB",
    "SUBSCR",
}
_OPTION_MARKERS = {"OPCAO", "OPC", "CALL", "PUT"}
_UNIT_MARKERS = {"UNT", "UNIT"}
_COMMON_SHARE_MARKERS = {"ON", "ON NM", "ON N1", "ON N2", "ON ED", "ON EJ"}
_PREFERRED_SHARE_MARKERS = {"PN", "PNA", "PNB", "PNC", "PND", "PN NM", "PN N1", "PN N2"}
_FUND_MARKERS = {"CI", "CIE", "CI ER", "CIED"}
_FII_NAME_PREFIXES = ("FII ", "FIAGRO ", "FIINFRA ", "FIP ", "FIDC ")
_ETF_NAME_MARKERS = ("ETF", "ISHARES", "IT NOW", "BB ETF", "TREND", "HASHDEX")


class CotahistAssetType(str, Enum):
    ACAO = "ACAO"
    FII = "FII"
    ETF_NACIONAL = "ETF_NACIONAL"
    BDR = "BDR"


class CotahistClassificationStatus(str, Enum):
    CLASSIFIED = "CLASSIFIED"
    INELEGIVEL = "INELEGIVEL"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class CotahistClassification:
    status: CotahistClassificationStatus
    asset_type: CotahistAssetType | None
    reason: str


@dataclass(frozen=True)
class CotahistRecord:
    """Subset canônico do registro 01 realmente consumível pelo SGI."""

    timestamp: datetime
    ticker: str
    market_type: str
    short_name: str
    specification: str
    currency: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    quotation_factor: int
    isin: str | None


def _normalized_specification(record: CotahistRecord) -> str:
    return " ".join(record.specification.upper().split())


def _normalized_short_name(record: CotahistRecord) -> str:
    return " ".join(record.short_name.upper().split())


def _contains_marker(specification: str, markers: set[str]) -> bool:
    tokens = set(specification.replace("/", " ").replace("-", " ").split())
    return any(marker in tokens or marker in specification for marker in markers)


def classify_cotahist_record(record: CotahistRecord) -> CotahistClassification:
    """Classifica um registro COTAHIST sem chamadas externas ou persistência."""
    if record.market_type not in _SUPPORTED_SPOT_MARKETS:
        return CotahistClassification(
            status=CotahistClassificationStatus.INELEGIVEL,
            asset_type=None,
            reason="unsupported_market_type",
        )

    specification = _normalized_specification(record)
    short_name = _normalized_short_name(record)
    if _contains_marker(specification, _OPTION_MARKERS):
        return CotahistClassification(
            status=CotahistClassificationStatus.INELEGIVEL,
            asset_type=None,
            reason="derivative_or_option",
        )

    if _contains_marker(specification, _RIGHTS_OR_RECEIPTS_MARKERS):
        return CotahistClassification(
            status=CotahistClassificationStatus.INELEGIVEL,
            asset_type=None,
            reason="rights_receipts_or_subscription",
        )

    if "BDR" in specification:
        return CotahistClassification(
            status=CotahistClassificationStatus.CLASSIFIED,
            asset_type=CotahistAssetType.BDR,
            reason="specification_bdr",
        )

    share_markers = _COMMON_SHARE_MARKERS | _PREFERRED_SHARE_MARKERS | _UNIT_MARKERS
    if _contains_marker(specification, share_markers):
        return CotahistClassification(
            status=CotahistClassificationStatus.CLASSIFIED,
            asset_type=CotahistAssetType.ACAO,
            reason="share_or_unit_specification",
        )

    if _contains_marker(specification, _FUND_MARKERS):
        if short_name.startswith(_FII_NAME_PREFIXES):
            return CotahistClassification(
                status=CotahistClassificationStatus.CLASSIFIED,
                asset_type=CotahistAssetType.FII,
                reason="fund_certificate_with_fii_name",
            )
        if any(marker in short_name for marker in _ETF_NAME_MARKERS):
            return CotahistClassification(
                status=CotahistClassificationStatus.CLASSIFIED,
                asset_type=CotahistAssetType.ETF_NACIONAL,
                reason="fund_certificate_with_etf_name",
            )
        return CotahistClassification(
            status=CotahistClassificationStatus.UNRESOLVED,
            asset_type=None,
            reason="fund_certificate_without_safe_fii_etf_signal",
        )

    return CotahistClassification(
        status=CotahistClassificationStatus.UNRESOLVED,
        asset_type=None,
        reason="unsupported_or_unknown_specification",
    )


def _decimal_cents(raw: str) -> Decimal:
    return Decimal(raw.strip()) / _CENTS


def parse_cotahist_record(line: str) -> CotahistRecord | None:
    """Extrai somente identidade/classificação/OHLCV necessários ao SGI.

    Campos de derivativos, ofertas, preço médio, contagem de negócios, quantidade
    negociada e distribuição são deliberadamente ignorados enquanto não houver
    consumidor canônico no domínio.
    """
    if len(line) < 245 or line[:2] != "01":
        return None

    market_type = line[24:27]
    if market_type not in _VALID_MARKETS:
        return None

    ticker = line[12:24].strip().upper()
    if not ticker:
        return None

    try:
        timestamp = datetime.strptime(line[2:10], "%Y%m%d").replace(
            tzinfo=timezone.utc
        )
        open_price = _decimal_cents(line[56:69])
        high_price = _decimal_cents(line[69:82])
        low_price = _decimal_cents(line[82:95])
        close_price = _decimal_cents(line[108:121])
        volume = _decimal_cents(line[170:188])
        quotation_factor = int(line[210:217])
    except (ArithmeticError, TypeError, ValueError):
        return None

    if close_price <= 0 or quotation_factor <= 0:
        return None

    isin = line[230:242].strip().upper() or None
    return CotahistRecord(
        timestamp=timestamp,
        ticker=ticker,
        market_type=market_type,
        short_name=line[27:39].strip(),
        specification=line[39:49].strip(),
        currency=line[52:56].strip(),
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=volume,
        quotation_factor=quotation_factor,
        isin=isin,
    )


def _parse_record_fields(line: str) -> tuple[str, datetime, float, str] | None:
    """Compatibilidade temporária do consumidor histórico de fechamento."""
    record = parse_cotahist_record(line)
    if record is None:
        return None
    return record.ticker, record.timestamp, float(record.close), record.market_type


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


def _parse_zip_records(payload: bytes) -> list[CotahistRecord]:
    records: list[CotahistRecord] = []
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".txt")]
        if not names:
            return []
        with archive.open(names[0]) as raw:
            for binary_line in raw:
                line = binary_line.decode("latin-1", errors="ignore").rstrip("\r\n")
                record = parse_cotahist_record(line)
                if record is not None:
                    records.append(record)
    return records


async def fetch_b3_cotahist_year_records(year: int) -> list[CotahistRecord]:
    """Baixa um arquivo anual e retorna registros COTAHIST parseados."""
    payload = await _download_year(year)
    if not payload:
        return []
    try:
        return _parse_zip_records(payload)
    except Exception as exc:
        logger.warning("[b3_cotahist] parse de registros falhou ano=%s erro=%s", year, exc)
        return []


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
