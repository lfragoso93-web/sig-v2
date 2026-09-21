"""Emite plano read-only para reconciliacao de eventos corporativos.

Uso dentro do container backend:
    python -m app.cli.corporate_event_reconciliation_dry_run \
      --decision CONFLICT --event-id 12 --event-id 13 --reason "duplicidade"
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from app.core.database import AsyncSessionLocal
from app.services.corporate_event_reconciliation_dry_run_service import (
    build_corporate_event_reconciliation_dry_run,
    execute_corporate_event_conflict_reconciliation,
    execute_corporate_event_matched_reconciliation,
)
from app.services.corporate_event_report_manifest import (
    verify_corporate_event_report_manifest,
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
    parser.add_argument("--event-id", type=int, action="append")
    parser.add_argument("--verify-report-file", type=Path)
    parser.add_argument("--verify-manifest-file", type=Path)
    parser.add_argument("--source-sha")
    parser.add_argument(
        "--ledger-preflight-event-id",
        type=int,
        help="Inclui o preflight read-only do evento no relatorio dry-run.",
    )
    parser.add_argument(
        "--report-file",
        type=Path,
        help="Salva o JSON do dry-run em um arquivo novo, sem sobrescrever.",
    )
    parser.add_argument(
        "--manifest-file",
        type=Path,
        help="Salva manifesto SHA-256 do report-file, sem sobrescrever.",
    )
    parser.add_argument(
        "--decision",
        choices=[item.value for item in CorporateEventReconciliationDecision],
        required=False,
    )
    parser.add_argument("--reason")
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
    verify_report_file = getattr(arguments, "verify_report_file", None)
    verify_manifest_file = getattr(arguments, "verify_manifest_file", None)
    if verify_report_file is not None or verify_manifest_file is not None:
        if verify_report_file is None or verify_manifest_file is None:
            raise ValueError(
                "verificacao exige --verify-report-file e --verify-manifest-file"
            )
        if any(
            bool(getattr(arguments, name, None))
            for name in (
                "event_id",
                "decision",
                "reason",
                "execute",
                "report_file",
                "manifest_file",
                "source_sha",
            )
        ):
            raise ValueError(
                "verificacao nao aceita argumentos de reconciliacao"
            )
        print(
            json.dumps(
                verify_corporate_event_report_manifest(
                    verify_report_file, verify_manifest_file
                ),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if not arguments.event_id or not arguments.decision or not arguments.reason:
        raise ValueError("dry-run exige --event-id, --decision e --reason")
    event_ids = tuple(arguments.event_id)
    decision = CorporateEventReconciliationDecision(arguments.decision)

    if arguments.execute and arguments.ledger_preflight_event_id is not None:
        raise ValueError(
            "ledger-preflight-event-id exige dry-run e nao aceita --execute"
        )
    if arguments.execute and arguments.report_file is not None:
        raise ValueError("report-file exige dry-run e nao aceita --execute")
    if arguments.execute and arguments.manifest_file is not None:
        raise ValueError("manifest-file exige dry-run e nao aceita --execute")
    if arguments.execute and arguments.source_sha is not None:
        raise ValueError("source-sha exige dry-run e nao aceita --execute")
    if arguments.manifest_file is not None and arguments.report_file is None:
        raise ValueError("manifest-file exige --report-file")
    if arguments.source_sha is not None and not re.fullmatch(
        r"[0-9a-fA-F]{40}", arguments.source_sha
    ):
        raise ValueError("source-sha deve ser SHA hexadecimal completo de 40 caracteres")
    if (
        arguments.ledger_preflight_event_id is not None
        and arguments.ledger_preflight_event_id not in event_ids
    ):
        raise ValueError(
            "ledger-preflight-event-id deve pertencer aos event-id informados"
        )

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
                ledger_preflight_event_id=arguments.ledger_preflight_event_id,
            )
            await db.rollback()

    payload: dict[str, Any] = report.to_dict()
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    report_bytes = f"{serialized}\n".encode("utf-8")
    if arguments.report_file is not None:
        try:
            with arguments.report_file.open("xb") as handle:
                handle.write(report_bytes)
        except FileExistsError:
            raise ValueError(
                f"report-file ja existe e nao sera sobrescrito: {arguments.report_file}"
            ) from None
        if arguments.manifest_file is not None:
            manifest = {
                "schema_version": "corporate-event-reconciliation-manifest.v1",
                "report_file": str(arguments.report_file),
                "report_sha256": hashlib.sha256(report_bytes).hexdigest(),
                "report_schema_version": payload.get("schema_version"),
                "dry_run": payload.get("dry_run"),
                "database_writes_executed": payload.get(
                    "database_writes_executed"
                ),
                "source_commit_sha": arguments.source_sha,
            }
            manifest_bytes = (
                json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n"
            ).encode("utf-8")
            try:
                with arguments.manifest_file.open("xb") as handle:
                    handle.write(manifest_bytes)
            except FileExistsError:
                raise ValueError(
                    f"manifest-file ja existe e nao sera sobrescrito: {arguments.manifest_file}"
                ) from None
    print(serialized)
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
