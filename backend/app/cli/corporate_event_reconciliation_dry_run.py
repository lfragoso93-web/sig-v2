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
    execute_corporate_event_matched_reconciliation,
)
from app.services.corporate_event_reconciliation_plan import (
    CorporateEventMatchEvidenceType,
    CorporateEventMatchResolutionEvidence,
    CorporateEventReconciliationDecision,
    FractionalResolutionPolicy,
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
        "--evidence-type",
        choices=[item.value for item in CorporateEventMatchEvidenceType],
    )
    parser.add_argument("--evidence-reference")
    parser.add_argument(
        "--fractional-policy",
        choices=[item.value for item in FractionalResolutionPolicy],
    )
    parser.add_argument("--fractional-quantity")
    parser.add_argument("--fractional-settlement-price")
    parser.add_argument("--cash-treatment")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Persiste reconciliacao CONFLICT ou MATCHED validada.",
    )
    return parser.parse_args()


async def _main(arguments: argparse.Namespace) -> int:
    event_ids = tuple(arguments.event_id)
    decision = CorporateEventReconciliationDecision(arguments.decision)

    match_argument_values = (
        arguments.evidence_type,
        arguments.evidence_reference,
        arguments.fractional_policy,
        arguments.fractional_quantity,
        arguments.fractional_settlement_price,
        arguments.cash_treatment,
    )
    has_match_arguments = any(value is not None for value in match_argument_values)

    match_resolution_evidence = None
    if decision == CorporateEventReconciliationDecision.MATCHED:
        if not arguments.evidence_type:
            raise ValueError("MATCHED exige --evidence-type")
        if not arguments.evidence_reference:
            raise ValueError("MATCHED exige --evidence-reference")
        if not arguments.fractional_policy:
            raise ValueError("MATCHED exige --fractional-policy")
        match_resolution_evidence = CorporateEventMatchResolutionEvidence(
            evidence_type=CorporateEventMatchEvidenceType(arguments.evidence_type),
            evidence_reference=arguments.evidence_reference,
            fractional_policy=FractionalResolutionPolicy(arguments.fractional_policy),
            fractional_quantity=arguments.fractional_quantity,
            fractional_settlement_price=arguments.fractional_settlement_price,
            cash_treatment=arguments.cash_treatment,
        )
    elif has_match_arguments:
        raise ValueError("CONFLICT nao aceita argumentos de evidencia de MATCHED")

    async with AsyncSessionLocal() as db:
        if arguments.execute:
            if decision == CorporateEventReconciliationDecision.CONFLICT:
                if arguments.canonical_event_id is not None:
                    raise ValueError("CONFLICT nao aceita canonical-event-id")
                report = await execute_corporate_event_conflict_reconciliation(
                    db,
                    event_ids=event_ids,
                    reason=arguments.reason,
                )
            else:
                if arguments.canonical_event_id is None:
                    raise ValueError("MATCHED exige --canonical-event-id")
                if match_resolution_evidence is None:
                    raise ValueError("MATCHED exige evidencia de reconciliacao")
                report = await execute_corporate_event_matched_reconciliation(
                    db,
                    event_ids=event_ids,
                    canonical_event_id=arguments.canonical_event_id,
                    reason=arguments.reason,
                    match_resolution_evidence=match_resolution_evidence,
                )
            await db.commit()
        else:
            report = await build_corporate_event_reconciliation_dry_run(
                db,
                event_ids=event_ids,
                decision=decision,
                reason=arguments.reason,
                canonical_event_id=arguments.canonical_event_id,
                match_resolution_evidence=match_resolution_evidence,
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
