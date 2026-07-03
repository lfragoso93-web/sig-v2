"""
Integração com o SGS/BCB para séries históricas de benchmarks.

Endpoint público usado:
https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json

O SGS pode responder 406 para intervalos muito grandes. Por isso, chamadas
históricas são divididas em janelas menores por padrão.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Iterable, Optional

import httpx

logger = logging.getLogger(__name__)

BCB_SGS_BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs"


@dataclass(frozen=True)
class SGSIndicator:
    indicator: str
    sgs_code: int
    frequency: str  # daily | monthly
    value_field: str  # rate_daily | rate_monthly


SGS_INDICATORS: dict[str, SGSIndicator] = {
    # Taxas diárias em % a.d.
    "SELIC": SGSIndicator("SELIC", 11, "daily", "rate_daily"),
    "CDI": SGSIndicator("CDI", 12, "daily", "rate_daily"),
    # Índices mensais em % a.m.
    "IPCA": SGSIndicator("IPCA", 433, "monthly", "rate_monthly"),
    "IGPM": SGSIndicator("IGPM", 189, "monthly", "rate_monthly"),
}


def _parse_bcb_date(value: str) -> date:
    return datetime.strptime(value, "%d/%m/%Y").date()


def _parse_decimal(value: str) -> Decimal:
    return Decimal(str(value).replace(",", "."))


def _format_bcb_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def _normalize_rows(meta: SGSIndicator, payload: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for item in payload or []:
        try:
            rows.append(
                {
                    "indicator": meta.indicator,
                    "date": _parse_bcb_date(item["data"]),
                    "value": _parse_decimal(item["valor"]),
                    "frequency": meta.frequency,
                    "value_field": meta.value_field,
                    "source": "BCB_SGS",
                    "sgs_code": meta.sgs_code,
                }
            )
        except Exception as exc:
            logger.warning("[BCB SGS] linha ignorada para %s: %s | %s", meta.indicator, item, exc)
    return rows


async def _fetch_sgs_window(
    client: httpx.AsyncClient,
    meta: SGSIndicator,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit_last: Optional[int] = None,
) -> list[dict]:
    if limit_last is not None:
        url = f"{BCB_SGS_BASE_URL}.{meta.sgs_code}/dados/ultimos/{limit_last}"
        params = {"formato": "json"}
    else:
        url = f"{BCB_SGS_BASE_URL}.{meta.sgs_code}/dados"
        params = {"formato": "json"}
        if start_date:
            params["dataInicial"] = _format_bcb_date(start_date)
        if end_date:
            params["dataFinal"] = _format_bcb_date(end_date)

    response = await client.get(url, params=params)

    # Algumas combinações do SGS retornam 406 quando dataFinal está muito à frente
    # ou quando o range é grande. Uma segunda tentativa sem dataFinal costuma
    # funcionar para buscar "desde dataInicial até o último dado disponível".
    if response.status_code == 406 and limit_last is None and end_date is not None:
        retry_params = dict(params)
        retry_params.pop("dataFinal", None)
        logger.warning(
            "[BCB SGS] 406 para %s de %s até %s; tentando sem dataFinal",
            meta.indicator,
            start_date,
            end_date,
        )
        response = await client.get(url, params=retry_params)

    response.raise_for_status()
    return _normalize_rows(meta, response.json())


def _windows(start_date: date, end_date: date, window_days: int) -> Iterable[tuple[date, date]]:
    current = start_date
    while current <= end_date:
        window_end = min(current + timedelta(days=window_days - 1), end_date)
        yield current, window_end
        current = window_end + timedelta(days=1)


async def fetch_sgs_series(
    indicator: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit_last: Optional[int] = None,
    timeout_seconds: float = 30.0,
) -> list[dict]:
    """Busca uma série SGS e retorna registros normalizados."""
    key = indicator.upper()
    if key not in SGS_INDICATORS:
        raise ValueError(f"Indicador SGS não suportado: {indicator}")

    meta = SGS_INDICATORS[key]
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        if limit_last is not None or not start_date or not end_date:
            return await _fetch_sgs_window(
                client,
                meta,
                start_date=start_date,
                end_date=end_date,
                limit_last=limit_last,
            )

        # Séries diárias são mais sensíveis a 406 em ranges grandes.
        # Mensais também são janeladas para manter comportamento uniforme.
        window_days = 370 if meta.frequency == "daily" else 3700
        rows: list[dict] = []
        seen: set[date] = set()
        for window_start, window_end in _windows(start_date, end_date, window_days):
            try:
                chunk = await _fetch_sgs_window(
                    client,
                    meta,
                    start_date=window_start,
                    end_date=window_end,
                )
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "[BCB SGS] falha na janela %s %s-%s: %s",
                    meta.indicator,
                    window_start,
                    window_end,
                    exc,
                )
                continue
            for row in chunk:
                row_date = row["date"]
                if row_date not in seen:
                    seen.add(row_date)
                    rows.append(row)
        return rows


async def fetch_many_sgs_series(
    indicators: Optional[Iterable[str]] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit_last: Optional[int] = None,
) -> dict[str, list[dict]]:
    selected = [i.upper() for i in (indicators or SGS_INDICATORS.keys())]
    result: dict[str, list[dict]] = {}
    for indicator in selected:
        result[indicator] = await fetch_sgs_series(
            indicator=indicator,
            start_date=start_date,
            end_date=end_date,
            limit_last=limit_last,
        )
    return result
