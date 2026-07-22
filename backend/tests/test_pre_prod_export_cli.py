from __future__ import annotations

import argparse
import json
from types import SimpleNamespace

import pytest

from app.cli import pre_prod_export as cli


def _arguments(tmp_path, **overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "artifact_root": tmp_path,
        "run_id": "20260722-120000",
        "branch": "stable-15jun",
        "commit_sha": "a" * 40,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class FakeSession:
    def __init__(self) -> None:
        self.executed: list[str] = []
        self.rollback_calls = 0
        self.close_calls = 0

    async def execute(self, statement):  # type: ignore[no-untyped-def]
        self.executed.append(str(statement))

    async def rollback(self) -> None:
        self.rollback_calls += 1

    async def close(self) -> None:
        self.close_calls += 1


def _cleanup(*, ok: bool = True):  # type: ignore[no-untyped-def]
    tables = [
        SimpleNamespace(
            name="transactions",
            row_count=2,
            proposed_action="export_required",
        ),
        SimpleNamespace(
            name="fixed_income_investments",
            row_count=1,
            proposed_action="export_required",
        ),
        SimpleNamespace(
            name="users",
            row_count=1,
            proposed_action="preserve",
        ),
    ]
    payload = {
        "schema_version": "pre-prod-cleanup-impact.v2",
        "ok": ok,
        "blockers": [] if ok else ["future_table"],
    }
    return SimpleNamespace(
        ok=ok,
        blockers=payload["blockers"],
        tables=tables,
        to_dict=lambda: payload,
    )


def _manifest(*, transaction_rows: int = 2):  # type: ignore[no-untyped-def]
    tables = [
        SimpleNamespace(table_name="transactions", row_count=transaction_rows),
        SimpleNamespace(table_name="fixed_income_investments", row_count=1),
    ]
    return SimpleNamespace(
        tables=tables,
        to_dict=lambda: {"schema_version": "pre-prod-export.v1"},
    )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"branch": "main"}, "branch stable-15jun"),
        ({"commit_sha": None}, "informe --commit-sha"),
        ({"commit_sha": "abc"}, "40 caracteres"),
        ({"run_id": "../escape"}, "run-id deve conter"),
    ],
)
def test_validate_arguments_rejects_unsafe_inputs(
    tmp_path,
    overrides: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(cli.PreProdExportCliError, match=message):
        cli._validate_arguments(_arguments(tmp_path, **overrides))


def test_reconcile_counts_accepts_same_snapshot() -> None:
    cli._reconcile_counts(_cleanup(), _manifest())


def test_reconcile_counts_rejects_divergence() -> None:
    with pytest.raises(cli.ExportReconciliationError, match="divergem"):
        cli._reconcile_counts(_cleanup(), _manifest(transaction_rows=3))


def test_publish_cleanup_impact_is_atomic_and_refuses_overwrite(tmp_path) -> None:
    run_directory = tmp_path / "run-1"
    destination = cli._publish_cleanup_impact(
        cleanup_impact=_cleanup(),
        run_directory=run_directory,
    )

    assert destination == run_directory / "cleanup-impact.json"
    assert destination.is_file()
    assert not (run_directory / ".cleanup-impact.json.tmp").exists()
    assert json.loads(destination.read_text(encoding="utf-8"))["ok"] is True

    with pytest.raises(FileExistsError, match="already exists"):
        cli._publish_cleanup_impact(
            cleanup_impact=_cleanup(),
            run_directory=run_directory,
        )


@pytest.mark.asyncio
async def test_main_uses_one_read_only_snapshot(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = FakeSession()
    cleanup = _cleanup()
    manifest = _manifest()
    run_directory = tmp_path / "20260722-120000"
    (run_directory / "export").mkdir(parents=True)

    monkeypatch.setattr(cli, "AsyncSessionLocal", lambda: session)

    async def fake_cleanup(**kwargs):  # type: ignore[no-untyped-def]
        assert kwargs["session"] is session
        assert kwargs["rollback_supplied_session"] is False
        return cleanup

    async def fake_export(**kwargs):  # type: ignore[no-untyped-def]
        assert kwargs["session"] is session
        assert kwargs["transaction_started"] is True
        return manifest

    monkeypatch.setattr(cli, "build_pre_prod_cleanup_impact", fake_cleanup)
    monkeypatch.setattr(cli, "build_pre_prod_export", fake_export)

    exit_code = await cli._main(_arguments(tmp_path))

    assert exit_code == 0
    assert "REPEATABLE READ, READ ONLY" in session.executed[0]
    assert session.rollback_calls >= 1
    assert session.close_calls == 1
    assert (run_directory / "cleanup-impact.json").is_file()
    output = capsys.readouterr().out
    assert '"reconciled": true' in output
    assert '"cleanup_impact_path"' in output


@pytest.mark.asyncio
async def test_main_blocks_before_export(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeSession()
    monkeypatch.setattr(cli, "AsyncSessionLocal", lambda: session)

    async def fake_cleanup(**_kwargs):  # type: ignore[no-untyped-def]
        return _cleanup(ok=False)

    async def unexpected_export(**_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("export must not run")

    monkeypatch.setattr(cli, "build_pre_prod_cleanup_impact", fake_cleanup)
    monkeypatch.setattr(cli, "build_pre_prod_export", unexpected_export)

    with pytest.raises(cli.ExportGateBlockedError):
        await cli._main(_arguments(tmp_path))

    assert session.rollback_calls == 1
    assert session.close_calls == 1
