"""Probe read-only de Yahoo max para historicos CRIPTO rasos."""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import date, datetime, timezone

import yfinance as yf

from app.cli import pre_prod_crypto_shallow_history_audit

MAX_TICKERS_PER_PROBE = 20


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Consulta Yahoo max para historicos CRIPTO rasos sem persistir dados."
    )
    parser.add_argument("--limit", type=int, default=MAX_TICKERS_PER_PROBE)
    parser.add_argument("--after-ticker", default=None)
    parser.add_argument("--required-to", default=None)
    return parser


def _yahoo_symbol(ticker: str) -> str:
    normalized = str(ticker or "").strip().upper()
    base = normalized[:-4] if normalized.endswith("-BRL") else normalized.split("-", 1)[0]
    return f"{base}-USD"


def _fetch_yahoo_max_probe(symbol: str) -> dict:
    try:
        history = yf.Ticker(symbol).history(period="max", interval="1d", auto_adjust=True)
    except Exception as exc:
        return {
            "ok": False,
            "symbol": symbol,
            "rows": 0,
            "first_date": None,
            "last_date": None,
            "error": str(exc),
        }
    if history.empty:
        return {
            "ok": True,
            "symbol": symbol,
            "rows": 0,
            "first_date": None,
            "last_date": None,
        }
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


async def _run(*, limit: int, after_ticker: str | None, required_to: date | None) -> dict:
    if limit < 1 or limit > MAX_TICKERS_PER_PROBE:
        raise SystemExit(f"--limit deve estar entre 1 e {MAX_TICKERS_PER_PROBE}")

    shallow = await pre_prod_crypto_shallow_history_audit._run(required_to=required_to)
    assets = list(shallow["assets"])
    normalized_after = str(after_ticker or "").strip().upper()
    if normalized_after:
        assets = [item for item in assets if str(item["ticker"]).upper() > normalized_after]
    selected = assets[:limit]

    probed = []
    available = 0
    unavailable = 0
    for item in selected:
        yahoo = await asyncio.to_thread(_fetch_yahoo_max_probe, _yahoo_symbol(str(item["ticker"])))
        has_history = bool(yahoo.get("rows", 0))
        available += int(has_history)
        unavailable += int(not has_history)
        probed.append(
            {
                **item,
                "coverage_class": (
                    "yahoo_history_available" if has_history else "yahoo_history_unavailable"
                ),
                "yahoo": yahoo,
            }
        )

    return {
        "read_only": True,
        "limit": limit,
        "after_ticker": normalized_after or None,
        "selected": len(probed),
        "by_coverage": {
            "yahoo_history_available": available,
            "yahoo_history_unavailable": unavailable,
        },
        "assets": probed,
    }


def main() -> None:
    args = _parser().parse_args()
    required_to = date.fromisoformat(args.required_to) if args.required_to else None
    print(
        json.dumps(
            asyncio.run(
                _run(
                    limit=args.limit,
                    after_ticker=args.after_ticker,
                    required_to=required_to,
                )
            ),
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
