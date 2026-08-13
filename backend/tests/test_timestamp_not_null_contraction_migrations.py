"""Gates para o endurecimento reversível dos timestamps compartilhados."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ROOT / "alembic" / "versions"

MIGRATIONS = (
    (
        "20260807_users_portfolios_timestamps_not_null.py",
        "20260807_users_portfolios_ts_nn",
        "20260807_drop_dup_rate_idx",
        ("users", "portfolios"),
    ),
    (
        "20260807_config_fixed_income_timestamps_not_null.py",
        "20260807_config_fixed_ts_nn",
        "20260807_users_portfolios_ts_nn",
        ("system_configs", "fixed_income_investments"),
    ),
    (
        "20260807_positions_snapshots_timestamps_not_null.py",
        "20260807_pos_snap_ts_nn",
        "20260807_config_fixed_ts_nn",
        ("portfolio_positions", "portfolio_snapshots"),
    ),
)


def _source(filename: str) -> str:
    return (VERSIONS / filename).read_text(encoding="utf-8")


def test_timestamp_hardening_chain_is_small_and_ordered() -> None:
    for filename, revision, down_revision, tables in MIGRATIONS:
        source = _source(filename)
        assert f'revision: str = "{revision}"' in source
        assert f'down_revision: str = "{down_revision}"' in source
        assert len(revision) <= 32
        for table in tables:
            assert f'"{table}"' in source


def test_timestamp_hardening_is_defensive_and_reversible() -> None:
    for filename, _, _, _ in MIGRATIONS:
        source = _source(filename)
        assert "SELECT COUNT(*)" in source
        assert "IS NULL" in source
        assert "raise RuntimeError" in source
        assert "nullable=False" in source
        assert "nullable=True" in source
        assert "UPDATE " not in source.upper()
        assert "DELETE " not in source.upper()
        assert "DROP TABLE" not in source.upper()
        assert "TRUNCATE" not in source.upper()
