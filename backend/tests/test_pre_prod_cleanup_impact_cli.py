from __future__ import annotations

import argparse
import json
from types import SimpleNamespace

import pytest

from app.cli import pre_prod_cleanup_impact as cli


def _arguments(tmp_path, **overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "artifact_root": tmp_path,
        "run_id": "20260722-120000",
        "branch": "stable-15jun",
        "commit_sha": "a" * 40,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class _FakeReport:
    def __init__(self, *, ok: bool) -> None:
        self.ok = ok

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "pre-prod-cleanup-impact.v2",
            "ok": self.ok,
            "blockers": [] if self.ok else ["future_table"],
        }


@pytest.mark.asyncio
async def test_main_writes_approved_report_and_returns_zero(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def fake_build(**kwargs: object) -> _FakeReport:
        assert kwargs == {"branch": "stable-15jun", "commit_sha": "a" * 40}
        return _FakeReport(ok=True)

    monkeypatch.setattr(cli, "build_pre_prod_cleanup_impact", fake_build)

    exit_code = await cli._main(_arguments(tmp_path))

    assert exit_code == 0
    report_path = tmp_path / "20260722-120000" / cli.REPORT_FILENAME
    assert json.loads(report_path.read_text(encoding="utf-8"))["ok"] is True

    output = json.loads(capsys.readouterr().out)
    assert output["run_id"] == "20260722-120000"
    assert output["report_path"] == str(report_path)
    assert output["report"]["schema_version"] == "pre-prod-cleanup-impact.v2"


@pytest.mark.asyncio
async def test_main_persists_blocked_report_and_returns_two(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_build(**_kwargs: object) -> _FakeReport:
        return _FakeReport(ok=False)

    monkeypatch.setattr(cli, "build_pre_prod_cleanup_impact", fake_build)

    exit_code = await cli._main(_arguments(tmp_path))

    assert exit_code == cli.BLOCKED_EXIT_CODE
    payload = json.loads(
        (tmp_path / "20260722-120000" / cli.REPORT_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    assert payload["ok"] is False
    assert payload["blockers"] == ["future_table"]


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
    with pytest.raises(cli.CleanupImpactCliError, match=message):
        cli._validate_arguments(_arguments(tmp_path, **overrides))


def test_write_report_refuses_to_overwrite_existing_run(tmp_path) -> None:
    arguments = _arguments(tmp_path)
    payload = {"schema_version": "pre-prod-cleanup-impact.v2", "ok": True}

    first_path = cli._write_report(
        artifact_root=arguments.artifact_root,
        run_id=arguments.run_id,
        payload=payload,
    )

    with pytest.raises(FileExistsError):
        cli._write_report(
            artifact_root=arguments.artifact_root,
            run_id=arguments.run_id,
            payload=payload,
        )

    assert json.loads(first_path.read_text(encoding="utf-8")) == payload


def test_write_report_uses_utf8_and_trailing_newline(tmp_path) -> None:
    report_path = cli._write_report(
        artifact_root=tmp_path,
        run_id="utf8",
        payload={"descrição": "limpeza não executada"},
    )

    content = report_path.read_text(encoding="utf-8")
    assert "descrição" in content
    assert "limpeza não executada" in content
    assert content.endswith("\n")
