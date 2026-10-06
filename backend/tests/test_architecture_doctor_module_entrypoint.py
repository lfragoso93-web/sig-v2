from pathlib import Path
import runpy

import pytest

from app.cli import architecture_doctor as cli


ENTRYPOINT = Path(__file__).resolve().parents[1] / "app" / "doctor" / "__main__.py"


def test_module_entrypoint_delegates_and_preserves_exit_code(monkeypatch) -> None:
    monkeypatch.setattr(cli, "main", lambda: 17)

    with pytest.raises(SystemExit) as raised:
        runpy.run_path(str(ENTRYPOINT), run_name="__main__")

    assert raised.value.code == 17
