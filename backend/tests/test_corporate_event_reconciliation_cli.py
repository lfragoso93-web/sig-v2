from argparse import Namespace

import pytest
from app.cli import corporate_event_reconciliation_dry_run as cli


def _arguments(
    *,
    decision: str,
    execute: bool = False,
    canonical_event_id: int | None = None,
    evidence_type: str | None = None,
    evidence_reference: str | None = None,
    fractional_policy: str | None = None,
    fractional_quantity: str | None = None,
    fractional_settlement_price: str | None = None,
    cash_treatment: str | None = None,
) -> Namespace:
    return Namespace(
        event_id=[12, 13],
        decision=decision,
        reason="reconciliacao de certificacao",
        canonical_event_id=canonical_event_id,
        evidence_type=evidence_type,
        evidence_reference=evidence_reference,
        fractional_policy=fractional_policy,
        fractional_quantity=fractional_quantity,
        fractional_settlement_price=fractional_settlement_price,
        cash_treatment=cash_treatment,
        execute=execute,
    )


@pytest.mark.asyncio
async def test_cli_matched_requires_evidence_type() -> None:
    with pytest.raises(ValueError, match="evidence-type"):
        await cli._main(
            _arguments(
                decision="MATCHED",
                canonical_event_id=13,
                evidence_reference="b3:official-document:AMOB3:2025-05",
                fractional_policy="NO_FRACTIONAL_RESIDUE",
            )
        )


@pytest.mark.asyncio
async def test_cli_matched_requires_evidence_reference() -> None:
    with pytest.raises(ValueError, match="evidence-reference"):
        await cli._main(
            _arguments(
                decision="MATCHED",
                canonical_event_id=13,
                evidence_type="OFFICIAL_EXCHANGE_DOCUMENT",
                fractional_policy="NO_FRACTIONAL_RESIDUE",
            )
        )


@pytest.mark.asyncio
async def test_cli_matched_requires_fractional_policy() -> None:
    with pytest.raises(ValueError, match="fractional-policy"):
        await cli._main(
            _arguments(
                decision="MATCHED",
                canonical_event_id=13,
                evidence_type="OFFICIAL_EXCHANGE_DOCUMENT",
                evidence_reference="b3:official-document:AMOB3:2025-05",
            )
        )


@pytest.mark.asyncio
async def test_cli_conflict_rejects_matched_evidence_arguments() -> None:
    with pytest.raises(
        ValueError,
        match="CONFLICT nao aceita argumentos de evidencia de MATCHED",
    ):
        await cli._main(
            _arguments(
                decision="CONFLICT",
                evidence_type="OFFICIAL_EXCHANGE_DOCUMENT",
                evidence_reference="b3:official-document:AMOB3:2025-05",
            )
        )


@pytest.mark.asyncio
async def test_cli_matched_execute_remains_forbidden(monkeypatch) -> None:
    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(cli, "AsyncSessionLocal", FakeSession)

    with pytest.raises(
        ValueError,
        match="execucao real permitida somente para CONFLICT",
    ):
        await cli._main(
            _arguments(
                decision="MATCHED",
                execute=True,
                canonical_event_id=13,
                evidence_type="OFFICIAL_EXCHANGE_DOCUMENT",
                evidence_reference="b3:official-document:AMOB3:2025-05",
                fractional_policy="NO_FRACTIONAL_RESIDUE",
            )
        )
