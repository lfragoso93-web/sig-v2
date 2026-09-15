"""Emite plano read-only para reconciliacao de eventos corporativos.

Uso dentro do container backend:
    python -m app.cli.corporate_event_reconciliation_dry_run \
      --decision CONFLICT --event-id 12 --event-id 13 --reason "duplicidade"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from app.core.database import AsyncSessionLocal
from app.services.corporate_event_reconciliation_dry_run_service import (
    build_corporate_event_reconciliation_dry_run,
    execute_corporate_event_conflict_reconciliation,
)
from app.services.corporate_event_reconciliation_plan import (
    CorporateEventReconciliationDecision,
)


def _configure_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="strict")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Gera um plano read-only de reconciliacao de eventos corporativos "
            "sem executar escrita no banco."
        )
    )
    parser.add_argument("--event-id", type=int, action="append", required=True)
    parser.add_argument(
        "--decision",
        choices=[item.value for item in CorporateEventReconciliationDecision],
        required=True,
    )
    parser.add_argument("--reason", required=True)
    parser.add_argument("--canonical-event-id", type=int)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Persiste apenas plano CONFLICT; MATCHED permanece somente dry-run.",
    )
    return parser.parse_args()


async def _main(arguments: argparse.Namespace) -> int:
    event_ids = tuple(arguments.event_id)
    decision = CorporateEventReconciliationDecision(arguments.decision)

    async with AsyncSessionLocal() as db:
        if arguments.execute:
            if decision != CorporateEventReconciliationDecision.CONFLICT:
                raise ValueError("execucao real permitida somente para CONFLICT")
            if arguments.canonical_event_id is not None:
                raise ValueError("CONFLICT nao aceita canonical-event-id")
            report = await execute_corporate_event_conflict_reconciliation(
                db,
                event_ids=event_ids,
                reason=arguments.reason,
            )
            await db.commit()
        else:
            report = await build_corporate_event_reconciliation_dry_run(
                db,
                event_ids=event_ids,
                decision=decision,
                reason=arguments.reason,
                canonical_event_id=arguments.canonical_event_id,
            )
            await db.rollback()

    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def main() -> None:
    _configure_output()
    try:
        exit_code = asyncio.run(_main(_arguments()))
    except KeyboardInterrupt:
        exit_code = 130
    except Exception as exc:  # noqa: BLE001 - boundary operacional da CLI
        print(
            json.dumps(
                {
                    "schema_version": "corporate-event-reconciliation-error.v1",
                    "ok": False,
                    "error": str(exc),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        exit_code = 1
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
