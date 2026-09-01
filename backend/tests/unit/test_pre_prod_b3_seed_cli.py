from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.cli import pre_prod_b3_seed as cli


class _FrozenDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 8, 31)


def _result(ok: bool = True):
    return SimpleNamespace(ok=ok, to_dict=lambda: {"ok": ok})


@pytest.mark.asyncio
async def test_b3_seed_cli_defaults_end_window_to_today(monkeypatch, capsys) -> None:
    runner = AsyncMock(return_value=_result())
    monkeypatch.setattr(cli, "date", _FrozenDate)
    monkeypatch.setattr(cli, "run_pre_prod_b3_seed", runner)
    monkeypatch.setattr("sys.argv", ["pre_prod_b3_seed", "--start-year", "2020"])

    exit_code = await cli._main()

    assert exit_code == 0
    assert '"ok": true' in capsys.readouterr().out
    runner.assert_awaited_once_with(
        start_year=2020,
        end_year=2026,
        cutoff_date=date(2026, 8, 31),
        include_catalog=True,
    )


@pytest.mark.asyncio
async def test_b3_seed_cli_preserves_explicit_end_window(monkeypatch) -> None:
    runner = AsyncMock(return_value=_result())
    monkeypatch.setattr(cli, "date", _FrozenDate)
    monkeypatch.setattr(cli, "run_pre_prod_b3_seed", runner)
    monkeypatch.setattr(
        "sys.argv",
        [
            "pre_prod_b3_seed",
            "--start-year",
            "2020",
            "--end-year",
            "2025",
            "--cutoff-date",
            "2025-12-30",
            "--history-only",
        ],
    )

    exit_code = await cli._main()

    assert exit_code == 0
    runner.assert_awaited_once_with(
        start_year=2020,
        end_year=2025,
        cutoff_date=date(2025, 12, 30),
        include_catalog=False,
    )
