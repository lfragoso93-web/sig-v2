"""
Cliente BRAPI — Dividendos de FIIs em lote.

Endpoint utilizado:
  GET /fiis/dividendos?symbols=HGLG11,XPML11&startDate=2018-01-01&endDate=2026-12-31

Documentoão: https://brapi.dev/docs/fiis/dividendos

Características:
  - Autenticação: Bearer token no header Authorization.
  - Máximo de 20 símbolos por chamada (limite documentado).
  - Parâmetros startDate / endDate opcionais no formato YYYY-MM-DD.
  - Retorna histórico de rendimentos e amortizações por símbolo.

Este client é distinto do brapi_dividends.py existente:
  - brapi_dividends.py  — sync por carteira, ticker a ticker, via /quote/{ticker}
  - este client         — bootstrap histórico em lote, via /fiis/dividendos

Rate limiting: reutiliza BRAPI_RATE_LIMIT / BRAPI_RATE_BURST de settings.
Retries: backoff exponencial em 429 e 5xx, até 3 tentativas.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import date
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = 30.0
_MAX_RETRIES = 3
_RETRY_STATUSES = {429, 500, 502, 503, 504}
_MAX_SYMBOLS_PER_REQUEST = 20  # Limite documentado da BRAPI


@dataclass
class FiiDividendEvent:
    """DTO normalizado de um evento de provento de FII retornado pela BRAPI."""
    ticker: str
    dividend_type: str          # Ex: 'RENDIMENTO', 'AMORTIZACAO'
    value_per_unit: float
    ex_date: Optional[date]
    payment_date: Optional[date]
    declared_date: Optional[date]
    raw_type: str               # Valor bruto original da BRAPI para auditoria


def _token() -> Optional[str]:
    return getattr(settings, "BRAPI_TOKEN", None) or None


def _is_configured() -> bool:
    tok = _token()
    return bool(tok and tok.strip())


def _build_headers() -> dict:
    tok = _token()
    if tok:
        return {"Authorization": f"Bearer {tok}"}
    return {}


def _parse_date(value: Optional[str]) -> Optional[date]:
    """Converte string ISO (YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SS) em date. Retorna None se inválido."""
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def _normalize_dividend_type(raw: str) -> str:
    """Normaliza o tipo de provento para o padrão interno do projeto."""
    mapping = {
        "RENDIMENTO": "RENDIMENTO",
        "AMORTIZACAO": "AMORTIZACAO",
        "AMORTIZAÇÃO": "AMORTIZACAO",
        "DIVIDENDO": "DIVIDENDO",
        "JCP": "JCP",
        "BONIFICACAO": "BONIFICACAO",
        "BONIFICAÇÃO": "BONIFICACAO",
    }
    return mapping.get(raw.upper().strip(), "OUTROS")


def _parse_events(ticker: str, raw_dividends: list[dict]) -> list[FiiDividendEvent]:
    """Converte a lista de dividendos brutos da BRAPI em lista de FiiDividendEvent."""
    events: list[FiiDividendEvent] = []
    for item in raw_dividends:
        try:
            # A BRAPI pode retornar os campos com nomes ligeiramente diferentes
            # dependendo da versão — tratamos as variantes conhecidas.
            value = float(
                item.get("value")
                or item.get("rate")
                or item.get("dividendValue")
                or 0
            )
            if value <= 0:
                continue

            raw_type = str(
                item.get("type")
                or item.get("dividendType")
                or "RENDIMENTO"
            )

            ex_date = _parse_date(
                item.get("lastDatePrior")
                or item.get("exDate")
                or item.get("ex_date")
            )
            payment_date = _parse_date(
                item.get("paymentDate")
                or item.get("payment_date")
            )
            declared_date = _parse_date(
                item.get("declaredDate")
                or item.get("approved_at")
            )

            events.append(FiiDividendEvent(
                ticker=ticker.upper(),
                dividend_type=_normalize_dividend_type(raw_type),
                value_per_unit=value,
                ex_date=ex_date,
                payment_date=payment_date,
                declared_date=declared_date,
                raw_type=raw_type,
            ))
        except Exception as e:
            logger.warning(
                "[brapi_fii_dividends] ticker=%s evento ignorado (parse error): %s | item=%s",
                ticker, e, item,
            )
            continue

    return events


async def _request_with_retry(
    client: httpx.AsyncClient,
    url: str,
    params: dict,
    headers: dict,
) -> Optional[dict]:
    """
    Executa GET com retry/backoff em 429 e 5xx.
    Retorna o JSON parsed ou None em caso de falha definitiva.
    """
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = await client.get(url, params=params, headers=headers)

            if resp.status_code in _RETRY_STATUSES:
                wait = 2 ** attempt
                logger.warning(
                    "[brapi_fii_dividends] HTTP %d na tentativa %d/%d — aguardando %ds",
                    resp.status_code, attempt, _MAX_RETRIES, wait,
                )
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(wait)
                    continue
                else:
                    logger.error(
                        "[brapi_fii_dividends] HTTP %d após %d tentativas — abortando lote",
                        resp.status_code, _MAX_RETRIES,
                    )
                    return None

            resp.raise_for_status()
            return resp.json()

        except httpx.TimeoutException as e:
            wait = 2 ** attempt
            logger.warning(
                "[brapi_fii_dividends] Timeout tentativa %d/%d: %s — aguardando %ds",
                attempt, _MAX_RETRIES, e, wait,
            )
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(wait)
            else:
                logger.error("[brapi_fii_dividends] Timeout definitivo após %d tentativas", _MAX_RETRIES)
                return None

        except Exception as e:
            logger.error("[brapi_fii_dividends] Erro inesperado na requisição: %s", e)
            return None

    return None


async def get_fii_dividends(
    symbols: list[str],
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    sort_order: str = "desc",
) -> list[FiiDividendEvent]:
    """
    Busca histórico de dividendos/rendimentos de FIIs via BRAPI.

    Args:
        symbols:    Lista de tickers (ex: ["HGLG11", "XPML11"]). Máximo 20.
        start_date: Data inicial do período (opcional, formato YYYY-MM-DD).
        end_date:   Data final do período (opcional, formato YYYY-MM-DD).
        sort_order: Ordem de retorno — 'asc' ou 'desc' (default: 'desc').

    Returns:
        Lista de FiiDividendEvent normalizados. Retorna [] se não configurado ou erro.

    Raises:
        ValueError: Se len(symbols) > 20 (limite BRAPI) ou lista vazia.
    """
    if not symbols:
        raise ValueError("[brapi_fii_dividends] symbols não pode ser vazio")

    if len(symbols) > _MAX_SYMBOLS_PER_REQUEST:
        raise ValueError(
            f"[brapi_fii_dividends] Máximo de {_MAX_SYMBOLS_PER_REQUEST} símbolos por chamada "
            f"(recebido: {len(symbols)}). Use chunks de até {_MAX_SYMBOLS_PER_REQUEST}."
        )

    if not _is_configured():
        logger.warning(
            "[brapi_fii_dividends] BRAPI_TOKEN não configurado — sync de dividendos FIIs ignorado"
        )
        return []

    url = f"{settings.BRAPI_BASE_URL}/fiis/dividendos"
    symbols_str = ",".join(s.upper().strip() for s in symbols)

    params: dict = {"symbols": symbols_str, "sortOrder": sort_order}
    if start_date:
        params["startDate"] = start_date.isoformat()
    if end_date:
        params["endDate"] = end_date.isoformat()

    headers = _build_headers()

    logger.info(
        "[brapi_fii_dividends] Buscando dividendos | symbols=%s | start=%s | end=%s",
        symbols_str,
        start_date.isoformat() if start_date else "n/a",
        end_date.isoformat() if end_date else "n/a",
    )

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        data = await _request_with_retry(client, url, params, headers)

    if data is None:
        return []

    # A BRAPI retorna { "dividends": { "HGLG11": [...], "XPML11": [...] } }
    # ou { "results": [ { "ticker": "HGLG11", "dividends": [...] } ] }
    # Suportamos ambos os formatos.
    all_events: list[FiiDividendEvent] = []

    dividends_root = data.get("dividends") or {}
    if dividends_root:
        # Formato dict: { "HGLG11": [...] }
        if isinstance(dividends_root, dict):
            for ticker, divs in dividends_root.items():
                if isinstance(divs, list):
                    parsed = _parse_events(ticker, divs)
                    logger.debug(
                        "[brapi_fii_dividends] %s: %d eventos parseados", ticker, len(parsed)
                    )
                    all_events.extend(parsed)
        # Formato lista: [ { "ticker": ..., "dividends": [...] } ]
        elif isinstance(dividends_root, list):
            for item in dividends_root:
                ticker = item.get("ticker", "")
                divs = item.get("dividends", [])
                if ticker and isinstance(divs, list):
                    parsed = _parse_events(ticker, divs)
                    logger.debug(
                        "[brapi_fii_dividends] %s: %d eventos parseados", ticker, len(parsed)
                    )
                    all_events.extend(parsed)
    else:
        # Tenta formato alternativo com 'results'
        results = data.get("results", [])
        for item in results:
            ticker = item.get("ticker", "")
            divs = (
                item.get("dividends")
                or item.get("dividendsData", {}).get("cashDividends", [])
                or []
            )
            if ticker and isinstance(divs, list):
                parsed = _parse_events(ticker, divs)
                logger.debug(
                    "[brapi_fii_dividends] %s: %d eventos parseados", ticker, len(parsed)
                )
                all_events.extend(parsed)

    logger.info(
        "[brapi_fii_dividends] Total: %d eventos de %d símbolos processados",
        len(all_events), len(symbols),
    )
    return all_events


async def get_fii_dividends_chunked(
    symbols: list[str],
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    sort_order: str = "desc",
    chunk_size: Optional[int] = None,
) -> list[FiiDividendEvent]:
    """
    Versão batch-safe de get_fii_dividends.

    Divide a lista de symbols em chunks do tamanho configurado em
    settings.DIVIDENDS_BATCH_SIZE (máx 20) e agrega os resultados.

    Use esta função no bootstrap para listas grandes de tickers.

    Args:
        symbols:    Lista de tickers sem limite prévio (será dividida automaticamente).
        start_date: Data inicial do período.
        end_date:   Data final do período.
        sort_order: Ordem de retorno.
        chunk_size: Override do batch size (default: settings.DIVIDENDS_BATCH_SIZE).

    Returns:
        Lista agregada de FiiDividendEvent de todos os chunks.
    """
    if not symbols:
        return []

    effective_chunk = min(
        chunk_size or settings.DIVIDENDS_BATCH_SIZE,
        _MAX_SYMBOLS_PER_REQUEST,
    )

    all_events: list[FiiDividendEvent] = []
    total_symbols = len(symbols)
    chunks = [
        symbols[i: i + effective_chunk]
        for i in range(0, total_symbols, effective_chunk)
    ]

    logger.info(
        "[brapi_fii_dividends] Bootstrap: %d símbolos em %d chunks de até %d",
        total_symbols, len(chunks), effective_chunk,
    )

    for idx, chunk in enumerate(chunks, start=1):
        logger.info(
            "[brapi_fii_dividends] Chunk %d/%d: %s",
            idx, len(chunks), ",".join(chunk),
        )
        try:
            events = await get_fii_dividends(
                symbols=chunk,
                start_date=start_date,
                end_date=end_date,
                sort_order=sort_order,
            )
            all_events.extend(events)
        except Exception as e:
            logger.error(
                "[brapi_fii_dividends] Chunk %d/%d falhou: %s — continuando com próximo chunk",
                idx, len(chunks), e,
            )
            # Falha parcial não aborta o bootstrap
            continue

    logger.info(
        "[brapi_fii_dividends] Bootstrap concluído: %d eventos totais de %d símbolos",
        len(all_events), total_symbols,
    )
    return all_events
