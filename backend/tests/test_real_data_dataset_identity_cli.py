from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.cli import real_data_dataset_identity as cli


def test_cli_emits_fail_closed_json_for_missing_artifact(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--artifact-directory", str(tmp_path / "missing")])

    assert exc_info.value.code == 1
    payload = json.loads(capsys.readouterr().err)
    assert payload["ok"] is False
    assert payload["database_writes_executed"] == 0
    assert payload["schema_version"] == "real-data-dataset-identity.v1"
