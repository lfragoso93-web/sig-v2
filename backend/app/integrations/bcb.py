"""
Integracao com a API PTAX do Banco Central do Brasil (BCB).

Fonte oficial e definitiva da cotacao USD/BRL (PTAX de venda).
API publica, sem autenticacao, sem limite de requests documentado.
Historico disponivel desde 1994.

Endpoints utilizados:
  CotacaoDolarPeriodo  - historico USD/BRL em range de datas
  CotacaoDolarDia      - cotacoes de um dia especifico (varios boletins)

IMPORTANTE: A API do BCB exige o formato de data MM-DD-YYYY (americano),
nao YYYY-MM-DD. A conversao e feita internamente neste modulo.

O campo retornado e cotacaoVenda (taxa de venda do dolar).
A dataHoraCotacao e no formato 'YYYY-MM-DD HH:MM:SS.mmm'.

Funcoes publicas:
  fetch_usd_brl_period(start_date, end_date) -> list[tuple[date, float]]
  fetch_usd_brl_day(date_str)               -> Optional[float]

Ambas retornam [] / None em caso de erro sem propagar excecao.
"""
from __future__ import annotations

import logging
from datetime import date as DateType
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata"
_TIMEOUT = 15.0
_SELECT = "cotacaoCompra,cotacaoVenda,dataHoraCotacao"


def _to_bcb_date(date_str: str) -> str:
    """
    Converte 'YYYY-MM-DD' para 'MM-DD-YYYY' exigido pela API do BCB.
    Aceita tambem objetos date convertidos para string.
    """
    d = DateType.fromisoformat(str(date_str)[:10])
    return d.strftime("%m-%d-%Y")


def _parse_bcb_rows(value: list[dict]) -> list[tuple[DateType, float]]:
    """
    Parseia a lista 'value' da resposta BCB.
    Usa cotacaoVenda como preco de referencia (PTAX venda).
    Ignora registros com preco zero ou ausente.
    """
    rows: list[tuple[DateType, float]] = []
    for item in value:
        price_str = item.get("cotacaoVenda") or item.get("cotacaoCompra")
        date_str = item.get("dataHoraCotacao", "")
        if not price_str or not date_str:
            continue
        try:
            price = float(price_str)
            if price <= 0:
                continue
            # 'YYYY-MM-DD HH:MM:SS.mmm' -> date
            d = DateType.fromisoformat(str(date_str)[:10])
            rows.append((d, price))
        except (ValueError, TypeError):
            continue
    # Remove duplicatas do mesmo dia mantendo o ultimo boletim (maior hora)
    by_date: dict[DateType, float] = {}
    for d, p in rows:
        by_date[d] = p  # sobrescreve com o mais recente (lista ja vem ordenada)
    result = sorted(by_date.items())
    return result


async def fetch_usd_brl_period(
    start_date: str,
    end_date: str,
) -> list[tuple[DateType, float]]:
    """
    Retorna historico diario de PTAX USD/BRL para o periodo.

    Parametros:
      start_date: 'YYYY-MM-DD'
      end_date:   'YYYY-MM-DD'

    Retorna lista de (date, cotacaoVenda) ordenada ASC.
    Retorna [] em caso de erro ou periodo sem dados (feriados/fins de semana).

    Nota: a API do BCB nao retorna dados para fins de semana e feriados.
    O fx_service trata isso buscando o dia util anterior mais proximo.
    """
    try:
        di = _to_bcb_date(start_date)
        df = _to_bcb_date(end_date)

        url = (
            f"{_BASE}/CotacaoDolarPeriodo"
            f"(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"
        )
        params = {
            "@dataInicial": f"'{di}'",
            "@dataFinalCotacao": f"'{df}'",
            "$format": "json",
            "$select": _SELECT,
            "$orderby": "dataHoraCotacao asc",
        }

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        value = data.get("value", [])
        if not value:
            logger.debug("[bcb] CotacaoDolarPeriodo %s a %s: sem dados (feriado/fim de semana?)", start_date, end_date)
            return []

        rows = _parse_bcb_rows(value)
        logger.info("[bcb] CotacaoDolarPeriodo %s a %s: %d registros", start_date, end_date, len(rows))
        return rows

    except Exception as e:
        logger.warning("[bcb] fetch_usd_brl_period %s a %s erro: %s", start_date, end_date, e)
        return []


async def fetch_usd_brl_day(date_str: str) -> Optional[float]:
    """
    Retorna a PTAX de venda USD/BRL para um dia especifico.
    Usa CotacaoDolarDia que retorna todos os boletins do dia (retorna o ultimo).
    Retorna None se nao houver dado (fim de semana, feriado ou erro).
    """
    try:
        d_bcb = _to_bcb_date(date_str)
        url = f"{_BASE}/CotacaoDolarDia(dataCotacao=@dataCotacao)"
        params = {
            "@dataCotacao": f"'{d_bcb}'",
            "$format": "json",
            "$select": _SELECT,
            "$orderby": "dataHoraCotacao desc",
            "$top": "1",
        }

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        value = data.get("value", [])
        if not value:
            logger.debug("[bcb] CotacaoDolarDia %s: sem dados", date_str)
            return None

        rows = _parse_bcb_rows(value)
        if not rows:
            return None

        price = rows[-1][1]
        logger.info("[bcb] CotacaoDolarDia %s = %.4f", date_str, price)
        return price

    except Exception as e:
        logger.warning("[bcb] fetch_usd_brl_day %s erro: %s", date_str, e)
        return None
