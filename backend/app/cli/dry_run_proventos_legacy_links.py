"""Gera o relatório de vínculos históricos possíveis sem alterar o banco."""

import argparse
import asyncio
import json

from app.core.database import AsyncSessionLocal
from app.services.proventos_legacy_link_service import dry_run_legacy_dividend_links


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simula vínculos de dividends legados com asset_dividends."
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="omite decisões individuais e imprime somente as contagens",
    )
    return parser.parse_args()


async def _run(*, include_details: bool) -> None:
    async with AsyncSessionLocal() as db:
        report = await dry_run_legacy_dividend_links(db)
    print(
        json.dumps(
            report.to_dict(include_details=include_details),
            indent=2,
            sort_keys=True,
        )
    )


def main() -> None:
    args = _arguments()
    asyncio.run(_run(include_details=not args.summary_only))


if __name__ == "__main__":
    main()
