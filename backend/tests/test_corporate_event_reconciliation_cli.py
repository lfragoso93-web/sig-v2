from argparse import Namespace

import pytest

from app.cli import corporate_event_reconciliation_dry_run as cli


def _arguments(
    *,
    decision: str,
    execute: bool = False,
    canonical_event_id: int | None = None,
    broker_statement_reference: str | None = None,
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
        broker_statement_reference=broker_statement_reference,
        fractional_policy=fractional_policy,
        fractional_quantity=fractional_quantity,
        fractional_settlement_price=fractional_settlement_price,
        cash_treatment=cash_treatment,
        execute=execute,
    )


@pytest.mark.asyncio
async def test_cli_matched_requires_broker_statement_reference() -> None:
    with pytest.raises(ValueError, match="broker-statement-reference"):
        await cli._main(
            _arguments(
                decision="MATCHED",
                canonical_event_id=13,
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
                broker_statement_reference="broker-note:AMOB3:2025-05",
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
                broker_statement_reference="broker-note:AMOB3:2025-05",
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
                broker_statement_reference="broker-note:AMOB3:2025-05",
                fractional_policy="NO_FRACTIONAL_RESIDUE",
            )
        )
