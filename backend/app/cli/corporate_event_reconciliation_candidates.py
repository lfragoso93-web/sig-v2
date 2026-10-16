"""Emite candidatos cross-provider sem reconciliar ou escrever no banco."""

from __future__ import annotations

import argparse
import asyncio
import json

from app.core.database import AsyncSessionLocal
from app.services.corporate_event_reconciliation_candidates import (
    load_cross_provider_candidates,
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Lista candidatos exatos de equivalência entre provedores; "
            "não altera estado de reconciliação."
        )
    )
    parser.add_argument("--ticker", help="Filtra por ticker contábil.")
    return parser.parse_args()


async def _main(ticker: str | None) -> dict:
    async with AsyncSessionLocal() as db:
        groups = await load_cross_provider_candidates(db, ticker=ticker)
    return {
        "schema_version": "corporate-event-reconciliation-candidates.v1",
        "read_only": True,
        "database_writes_executed": 0,
        "automatic_match_allowed": False,
        "candidate_group_count": len(groups),
        "candidate_groups": [
            {
                "ticker": group.ticker,
                "event_type": group.event_type,
                "effective_date": group.effective_date.isoformat(),
                "quantity_factor": str(group.quantity_factor),
                "review_required": group.review_required,
                "events": [
                    {
                        "event_id": event.event_id,
                        "source_provider": event.source_provider,
                        "source_event_id": event.source_event_id,
                    }
                    for event in group.events
                ],
            }
            for group in groups
        ],
    }


def main() -> None:
    arguments = _arguments()
    print(
        json.dumps(
            asyncio.run(_main(arguments.ticker)),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
