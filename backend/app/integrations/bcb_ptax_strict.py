"""Cliente estrito da PTAX de venda para o seed cambial pré-produção.

Este módulo realiza somente leitura da API oficial do Banco Central do Brasil.
Não persiste dados, não usa cache e não aplica fontes alternativas ou taxa fixa.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date as DateType, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

PTAX_BASE_URL = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata"
PTAX_TIMEOUT_SECONDS = 15.0
PTAX_SOURCE = "BCB"
PTAX_RATE_TYPE = "PTAX_SELL"
PTAX_PAIR = "USD-BRL"


class StrictPtaxError(RuntimeError):
    """Falha operacional ou contratual ao consultar a PTAX oficial."""


@dataclass(frozen=True)
class StrictPtaxRate:
    pair: str
    rate_date: DateType
    rate: Decimal
    quoted_at: datetime
    source: str = PTAX_SOURCE
    rate_type: str = PTAX_RATE_TYPE

    def __post_init__(self) -> None:
        if self.pair != PTAX_PAIR:
            raise StrictPtaxError(f"par não suportado: {self.pair!r}")
        if self.source != PTAX_SOURCE:
            raise StrictPtaxError(f"fonte não suportada: {self.source!r}")
        if self.rate_type != PTAX_RATE_TYPE:
            raise StrictPtaxError(f"tipo de taxa não suportado: {self.rate_type!r}")
        if self.rate <= 0:
            raise StrictPtaxError("rate deve ser positivo")
        if self.quoted_at.date() != self.rate_date:
            raise StrictPtaxError("quoted_at deve pertencer a rate_date")


def _parse_iso_date(value: str | DateType) -> DateType:
    if isinstance(value, DateType):
        return value
    try:
        return DateType.fromisoformat(str(value))
    except ValueError as exc:
        raise StrictPtaxError(f"data inválida: {value!r}") from exc


def _to_bcb_date(value: DateType) -> str:
    return value.strftime("%m-%d-%Y")


def _parse_quoted_at(value: Any) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise StrictPtaxError("dataHoraCotacao ausente")
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise StrictPtaxError(f"dataHoraCotacao inválida: {text!r}") from exc


def _parse_rate(value: Any) -> Decimal:
    if value is None or value == "":
        raise StrictPtaxError("cotacaoVenda ausente")
    try:
        rate = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise StrictPtaxError(f"cotacaoVenda inválida: {value!r}") from exc
    if rate <= 0:
        raise StrictPtaxError("cotacaoVenda deve ser positiva")
    return rate


def parse_strict_ptax_rows(value: Any) -> tuple[StrictPtaxRate, ...]:
    """Converte a resposta BCB em taxas tipadas e deduplicadas por data."""
    if not isinstance(value, list):
        raise StrictPtaxError("campo value deve ser uma lista")

    by_date: dict[DateType, StrictPtaxRate] = {}
    for item in value:
        if not isinstance(item, dict):
            raise StrictPtaxError("cada item de value deve ser um objeto")
        quoted_at = _parse_quoted_at(item.get("dataHoraCotacao"))
        rate = StrictPtaxRate(
            pair=PTAX_PAIR,
            rate_date=quoted_at.date(),
            rate=_parse_rate(item.get("cotacaoVenda")),
            quoted_at=quoted_at,
        )
        current = by_date.get(rate.rate_date)
        if current is None or rate.quoted_at > current.quoted_at:
            by_date[rate.rate_date] = rate

    return tuple(by_date[key] for key in sorted(by_date))


async def fetch_strict_usd_brl_period(
    start_date: str | DateType,
    end_date: str | DateType,
    *,
    client: httpx.AsyncClient | None = None,
) -> tuple[StrictPtaxRate, ...]:
    """Busca PTAX de venda oficial; qualquer falha é propagada como StrictPtaxError."""
    start = _parse_iso_date(start_date)
    end = _parse_iso_date(end_date)
    if start > end:
        raise StrictPtaxError("start_date não pode ser posterior a end_date")

    url = (
        f"{PTAX_BASE_URL}/CotacaoDolarPeriodo"
        "(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"
    )
    params = {
        "@dataInicial": f"'{_to_bcb_date(start)}'",
        "@dataFinalCotacao": f"'{_to_bcb_date(end)}'",
        "$format": "json",
        "$select": "cotacaoVenda,dataHoraCotacao",
    }

    owns_client = client is None
    active_client = client or httpx.AsyncClient(timeout=PTAX_TIMEOUT_SECONDS)
    try:
        response = await active_client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise StrictPtaxError("resposta PTAX deve ser um objeto JSON")
        rows = parse_strict_ptax_rows(payload.get("value"))
        if not rows:
            raise StrictPtaxError(
                f"BCB não retornou PTAX de venda entre {start.isoformat()} e {end.isoformat()}"
            )
        return rows
    except StrictPtaxError:
        raise
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise StrictPtaxError(
            f"falha ao consultar PTAX oficial entre {start.isoformat()} e {end.isoformat()}"
        ) from exc
    finally:
        if owns_client:
            await active_client.aclose()
