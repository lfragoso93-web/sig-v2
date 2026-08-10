"""Probe read-only de provedores para um conjunto explicito de criptoativos."""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone

import yfinance as yf

from app.integrations.brapi_crypto_history import fetch_brapi_crypto_history


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Consulta BRAPI/Yahoo para tickers CRIPTO sem persistir dados."
    )
    parser.add_argument("--ticker", action="append", default=None)
    return parser


def _normalize_tickers(values: list[str] | None) -> list[str]:
    tickers = sorted({str(value).strip().upper() for value in values or [] if str(value).strip()})
    if not tickers:
        raise SystemExit("informe ao menos um --ticker")
    return tickers


def _yahoo_symbol(ticker: str) -> str:
    base = ticker[:-4] if ticker.endswith("-BRL") else ticker.split("-", 1)[0]
    return f"{base}-USD"


def _fetch_yahoo_probe(symbol: str) -> dict:
    try:
        history = yf.Ticker(symbol).history(period="5d", interval="1d", auto_adjust=True)
    except Exception as exc:
        return {"ok": False, "symbol": symbol, "rows": 0, "error": str(exc)}
    if history.empty:
        return {"ok": True, "symbol": symbol, "rows": 0, "first_date": None, "last_date": None}
    dates: list[datetime] = []
    for value in history.index:
        ts = value.to_pydatetime()
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        else:
            ts = ts.astimezone(timezone.utc)
        dates.append(ts)
    return {
        "ok": True,
        "symbol": symbol,
        "rows": len(history),
        "first_date": min(dates).date().isoformat() if dates else None,
        "last_date": max(dates).date().isoformat() if dates else None,
    }


async def _probe_one(ticker: str) -> dict:
    brapi: dict
    try:
        rows = await fetch_brapi_crypto_history(
            ticker,
            currency="BRL",
            range_="5d",
            interval="1d",
        )
        brapi = {
            "ok": True,
            "rows": len(rows),
            "first_date": rows[0][0].date().isoformat() if rows else None,
            "last_date": rows[-1][0].date().isoformat() if rows else None,
        }
    except Exception as exc:
        brapi = {"ok": False, "rows": 0, "error": str(exc)}

    yahoo = await asyncio.to_thread(_fetch_yahoo_probe, _yahoo_symbol(ticker))
    return {"ticker": ticker, "brapi": brapi, "yahoo": yahoo}


async def _run(tickers: list[str]) -> dict:
    results = []
    for ticker in tickers:
        results.append(await _probe_one(ticker))
    return {
        "read_only": True,
        "requested": len(tickers),
        "assets": results,
    }


def main() -> None:
    args = _parser().parse_args()
    tickers = _normalize_tickers(args.ticker)
    print(json.dumps(asyncio.run(_run(tickers)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
