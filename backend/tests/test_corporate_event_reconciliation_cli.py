from argparse import Namespace
import hashlib
import json

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
    report_file=None,
    manifest_file=None,
    verify_report_file=None,
    verify_manifest_file=None,
    event_ids=None,
    reason="reconciliacao de certificacao",
    source_sha=None,
) -> Namespace:
    return Namespace(
        event_id=[12, 13] if event_ids is None else event_ids,
        decision=decision,
        reason=reason,
        canonical_event_id=canonical_event_id,
        evidence_type=evidence_type,
        evidence_reference=evidence_reference,
        fractional_policy=fractional_policy,
        fractional_quantity=fractional_quantity,
        fractional_settlement_price=fractional_settlement_price,
        cash_treatment=cash_treatment,
        ledger_preflight_event_id=ledger_preflight_event_id,
        report_file=report_file,
        manifest_file=manifest_file,
        verify_report_file=verify_report_file,
        verify_manifest_file=verify_manifest_file,
        source_sha=source_sha,
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
async def test_cli_report_file_requires_dry_run(tmp_path) -> None:
    with pytest.raises(ValueError, match="report-file exige dry-run"):
        await cli._main(
            _arguments(
                decision="CONFLICT",
                execute=True,
                report_file=tmp_path / "report.json",
            )
        )


def test_cli_report_file_is_exclusive_and_writes_json(tmp_path) -> None:
    report_file = tmp_path / "report.json"
    payload = {"schema_version": "test.v1", "database_writes_executed": 0}
    serialized = json.dumps(payload, indent=2, sort_keys=True)

    with report_file.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(serialized)
        handle.write("\n")

    assert json.loads(report_file.read_text(encoding="utf-8")) == payload
    with pytest.raises(FileExistsError):
        report_file.open("x", encoding="utf-8")


@pytest.mark.asyncio
async def test_cli_verify_mode_is_read_only_and_does_not_open_session(
    monkeypatch, tmp_path
) -> None:
    report_file = tmp_path / "report.json"
    manifest_file = tmp_path / "manifest.json"
    monkeypatch.setattr(
        cli,
        "verify_corporate_event_report_manifest",
        lambda report, manifest: {
            "valid": True,
            "report_sha256": "abc",
        },
    )

    result = await cli._main(
        _arguments(
            decision=None,
            event_ids=[],
            reason=None,
            verify_report_file=report_file,
            verify_manifest_file=manifest_file,
        )
    )

    assert result == 0


@pytest.mark.asyncio
async def test_cli_verify_mode_checks_retained_fixture_without_database(
    tmp_path,
) -> None:
    report_file = tmp_path / "report.json"
    manifest_file = tmp_path / "manifest.json"
    report_bytes = (
        json.dumps(
            {
                "schema_version": "corporate-event-reconciliation-dry-run.v2",
                "dry_run": True,
                "database_writes_executed": 0,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    report_file.write_bytes(report_bytes)
    manifest_file.write_text(
        json.dumps(
            {
                "schema_version": "corporate-event-reconciliation-manifest.v1",
                "report_file": str(report_file),
                "report_sha256": hashlib.sha256(report_bytes).hexdigest(),
                "report_schema_version": "corporate-event-reconciliation-dry-run.v2",
                "dry_run": True,
                "database_writes_executed": 0,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    result = await cli._main(
        _arguments(
            decision=None,
            event_ids=[],
            reason=None,
            verify_report_file=report_file,
            verify_manifest_file=manifest_file,
        )
    )

    assert result == 0


@pytest.mark.asyncio
async def test_cli_verify_mode_requires_both_artifacts(tmp_path) -> None:
    with pytest.raises(ValueError, match="exige --verify-report-file"):
        await cli._main(
            _arguments(
                decision=None,
                event_ids=[],
                reason=None,
                verify_report_file=tmp_path / "report.json",
            )
        )


@pytest.mark.asyncio
async def test_cli_manifest_requires_report_file(tmp_path) -> None:
    with pytest.raises(ValueError, match="manifest-file exige --report-file"):
        await cli._main(
            _arguments(
                decision="CONFLICT",
                manifest_file=tmp_path / "manifest.json",
            )
        )


@pytest.mark.asyncio
async def test_cli_source_sha_requires_full_hex_commit() -> None:
    with pytest.raises(ValueError, match="40 caracteres"):
        await cli._main(
            _arguments(decision="CONFLICT", source_sha="abc123")
        )


@pytest.mark.asyncio
async def test_cli_dry_run_writes_report_manifest_with_sha256(monkeypatch, tmp_path) -> None:
    class FakeReport:
        def to_dict(self):
            return {
                "schema_version": "test.v1",
                "dry_run": True,
                "database_writes_executed": 0,
            }

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def rollback(self):
            return None

    monkeypatch.setattr(cli, "AsyncSessionLocal", lambda: FakeSession())
    async def fake_dry_run(*args, **kwargs):
        return FakeReport()

    monkeypatch.setattr(cli, "build_corporate_event_reconciliation_dry_run", fake_dry_run)
    report_file = tmp_path / "report.json"
    manifest_file = tmp_path / "manifest.json"

    await cli._main(
        _arguments(
            decision="CONFLICT",
            report_file=report_file,
            manifest_file=manifest_file,
            source_sha="a" * 40,
        )
    )

    report_bytes = report_file.read_bytes()
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "corporate-event-reconciliation-manifest.v1"
    assert manifest["report_sha256"] == hashlib.sha256(report_bytes).hexdigest()
    assert manifest["report_schema_version"] == "test.v1"
    assert manifest["source_commit_sha"] == "a" * 40


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
async def test_cli_dry_run_forwards_ledger_preflight_and_rolls_back(monkeypatch) -> None:
    calls = []
    session = None

    class FakeReport:
        def to_dict(self):
            return {
                "schema_version": "corporate-event-reconciliation-dry-run.v2",
                "database_writes_executed": 0,
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

    async def fake_dry_run(db, **kwargs):
        calls.append({"db": db, **kwargs})
        return FakeReport()

    monkeypatch.setattr(cli, "AsyncSessionLocal", FakeSessionFactory())
    monkeypatch.setattr(
        cli,
        "build_corporate_event_reconciliation_dry_run",
        fake_dry_run,
    )

    result = await cli._main(
        _arguments(
            decision="CONFLICT",
            ledger_preflight_event_id=12,
        )
    )

    assert result == 0
    assert session is not None
    assert session.commits == 0
    assert session.rollbacks == 1
    assert len(calls) == 1
    assert calls[0]["ledger_preflight_event_id"] == 12
    assert calls[0]["event_ids"] == (12, 13)


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
