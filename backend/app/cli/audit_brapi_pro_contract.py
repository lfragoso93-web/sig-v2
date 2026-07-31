"""Audita contratos BRAPI Pro sem alterar o banco de dados."""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, date, datetime
from pathlib import Path

import httpx

from app.integrations.brapi_v2_client import BrapiV2Client
from app.services.brapi_contract_audit_service import (
    BrapiStockDividendsFetcher,
    audit_brapi_pro_contract,
)

DEFAULT_TICKERS = "AERI3,ITSA4,PETR4,VVAR3,MXRF11"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tickers", default=DEFAULT_TICKERS)
    parser.add_argument(
        "--date-from", type=date.fromisoformat, default=date(2000, 1, 1)
    )
    parser.add_argument(
        "--date-to", type=date.fromisoformat, default=datetime.now(UTC).date()
    )
    parser.add_argument("--output", type=Path)
    return parser


async def _run(arguments: argparse.Namespace) -> str:
    tickers = [item.strip() for item in arguments.tickers.split(",") if item.strip()]
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        brapi = BrapiV2Client()
        fetcher = BrapiStockDividendsFetcher(client=http_client)
        report = await audit_brapi_pro_contract(
            tickers=tickers,
            date_from=arguments.date_from,
            date_to=arguments.date_to,
            client=brapi,
            dividend_fetcher=fetcher,
        )
    return report.to_json()


def main() -> None:
    arguments = _parser().parse_args()
    payload = asyncio.run(_run(arguments))
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(payload + "\n", encoding="utf-8")
        print(arguments.output.resolve())
        return
    print(payload)


if __name__ == "__main__":
    main()
