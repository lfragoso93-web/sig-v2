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
    ledger_preflight_event_id: int | None = None,
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
        ledger_preflight_event_id=ledger_preflight_event_id,
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
async def test_cli_ledger_preflight_requires_dry_run() -> None:
    with pytest.raises(ValueError, match="exige dry-run"):
        await cli._main(
            _arguments(
                decision="CONFLICT",
                execute=True,
                ledger_preflight_event_id=12,
            )
        )


@pytest.mark.asyncio
async def test_cli_ledger_preflight_event_must_be_in_event_ids() -> None:
    with pytest.raises(ValueError, match="deve pertencer"):
        await cli._main(
            _arguments(
                decision="CONFLICT",
                ledger_preflight_event_id=99,
            )
        )


@pytest.mark.asyncio
async def test_cli_matched_execute_dispatches_writer_and_commits(
    monkeypatch,
) -> None:
    calls = []
    session = None

    class FakeReport:
        def to_dict(self):
            return {
                "schema_version": "test.v1",
                "decision": "MATCHED",
            }

    class FakeSession:
        def __init__(self):
            self.commits = 0
            self.rollbacks = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def commit(self):
            self.commits += 1

        async def rollback(self):
            self.rollbacks += 1

    class FakeSessionFactory:
        def __call__(self):
            nonlocal session
            session = FakeSession()
            return session

    async def fake_matched_writer(
        db,
        *,
        event_ids,
        canonical_event_id,
        reason,
        match_resolution_evidence,
    ):
        calls.append(
            {
                "db": db,
                "event_ids": event_ids,
                "canonical_event_id": canonical_event_id,
                "reason": reason,
                "evidence": match_resolution_evidence,
            }
        )
        return FakeReport()

    monkeypatch.setattr(cli, "AsyncSessionLocal", FakeSessionFactory())
    monkeypatch.setattr(
        cli,
        "execute_corporate_event_matched_reconciliation",
        fake_matched_writer,
    )

    result = await cli._main(
        _arguments(
            decision="MATCHED",
            execute=True,
            canonical_event_id=13,
            evidence_type="OFFICIAL_EXCHANGE_DOCUMENT",
            evidence_reference="b3:official-document:AMOB3:2025-05",
            fractional_policy="NO_FRACTIONAL_RESIDUE",
        )
    )

    assert result == 0
    assert session is not None
    assert session.commits == 1
    assert session.rollbacks == 0

    assert len(calls) == 1
    call = calls[0]
    assert call["db"] is session
    assert call["event_ids"] == (12, 13)
    assert call["canonical_event_id"] == 13
    assert call["reason"] == "reconciliacao de certificacao"
    assert (
        call["evidence"].evidence_type.value
        == "OFFICIAL_EXCHANGE_DOCUMENT"
    )
    assert (
        call["evidence"].evidence_reference
        == "b3:official-document:AMOB3:2025-05"
    )
    assert (
        call["evidence"].fractional_policy.value
        == "NO_FRACTIONAL_RESIDUE"
    )


@pytest.mark.asyncio
async def test_cli_matched_execute_requires_canonical_event_id(
    monkeypatch,
) -> None:
    writer_called = False
    session = None

    class FakeSession:
        def __init__(self):
            self.commits = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def commit(self):
            self.commits += 1

        async def rollback(self):
            return None

    class FakeSessionFactory:
        def __call__(self):
            nonlocal session
            session = FakeSession()
            return session

    async def fake_matched_writer(*args, **kwargs):
        nonlocal writer_called
        writer_called = True
        raise AssertionError("writer nao deveria ser chamado")

    monkeypatch.setattr(cli, "AsyncSessionLocal", FakeSessionFactory())
    monkeypatch.setattr(
        cli,
        "execute_corporate_event_matched_reconciliation",
        fake_matched_writer,
    )

    with pytest.raises(ValueError, match="canonical-event-id"):
        await cli._main(
            _arguments(
                decision="MATCHED",
                execute=True,
                evidence_type="OFFICIAL_EXCHANGE_DOCUMENT",
                evidence_reference="b3:official-document:AMOB3:2025-05",
                fractional_policy="NO_FRACTIONAL_RESIDUE",
            )
        )

    assert writer_called is False
    assert session is not None
    assert session.commits == 0


@pytest.mark.asyncio
async def test_cli_matched_execute_does_not_commit_writer_failure(
    monkeypatch,
) -> None:
    session = None

    class FakeSession:
        def __init__(self):
            self.commits = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def commit(self):
            self.commits += 1

        async def rollback(self):
            return None

    class FakeSessionFactory:
        def __call__(self):
            nonlocal session
            session = FakeSession()
            return session

    async def failing_matched_writer(*args, **kwargs):
        raise ValueError("evidencia divergente")

    monkeypatch.setattr(cli, "AsyncSessionLocal", FakeSessionFactory())
    monkeypatch.setattr(
        cli,
        "execute_corporate_event_matched_reconciliation",
        failing_matched_writer,
    )

    with pytest.raises(ValueError, match="evidencia divergente"):
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

    assert session is not None
    assert session.commits == 0


@pytest.mark.asyncio
async def test_cli_conflict_execute_preserves_existing_dispatch(
    monkeypatch,
) -> None:
    conflict_calls = []
    matched_called = False
    session = None

    class FakeReport:
        def to_dict(self):
            return {
                "schema_version": "test.v1",
                "decision": "CONFLICT",
            }

    class FakeSession:
        def __init__(self):
            self.commits = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def commit(self):
            self.commits += 1

        async def rollback(self):
            return None

    class FakeSessionFactory:
        def __call__(self):
            nonlocal session
            session = FakeSession()
            return session

    async def fake_conflict_writer(db, *, event_ids, reason):
        conflict_calls.append(
            {
                "db": db,
                "event_ids": event_ids,
                "reason": reason,
            }
        )
        return FakeReport()

    async def forbidden_matched_writer(*args, **kwargs):
        nonlocal matched_called
        matched_called = True
        raise AssertionError("MATCHED writer nao deveria ser chamado")

    monkeypatch.setattr(cli, "AsyncSessionLocal", FakeSessionFactory())
    monkeypatch.setattr(
        cli,
        "execute_corporate_event_conflict_reconciliation",
        fake_conflict_writer,
    )
    monkeypatch.setattr(
        cli,
        "execute_corporate_event_matched_reconciliation",
        forbidden_matched_writer,
    )

    result = await cli._main(
        _arguments(
            decision="CONFLICT",
            execute=True,
        )
    )

    assert result == 0
    assert session is not None
    assert session.commits == 1
    assert matched_called is False

    assert len(conflict_calls) == 1
    assert conflict_calls[0]["db"] is session
    assert conflict_calls[0]["event_ids"] == (12, 13)
    assert conflict_calls[0]["reason"] == "reconciliacao de certificacao"
