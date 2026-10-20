from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_MIGRATION_PATH = (
    _BACKEND_ROOT / "alembic" / "versions" / "20261009_market_calendar_days.py"
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "market_calendar_migration",
        _MIGRATION_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_calendar_migration_precedes_the_explicit_runtime_target() -> None:
    migration = _load_migration()
    config_migration = (
        _BACKEND_ROOT
        / "alembic"
        / "versions"
        / "20261010_b3_calendar_config_defaults.py"
    ).read_text(encoding="utf-8")
    entrypoint = (_BACKEND_ROOT / "entrypoint.sh").read_text(encoding="utf-8")

    assert migration.revision == "20261009_market_calendar"
    assert migration.down_revision == "20261008_treasury_instruments"
    assert 'down_revision: str = "20261009_market_calendar"' in config_migration
    assert 'RUNTIME_MIGRATION_TARGET="${RUNTIME_MIGRATION_TARGET:-20261019_corp_event_legs}"' in entrypoint
