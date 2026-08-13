"""Protege o gate autorizado de reset do banco local de testes."""

from __future__ import annotations

from app.governance.alembic_metadata_drift_policy import LOCAL_TEST_DB_RESET_RULES


def test_policy_requires_explicit_local_test_database_scope() -> None:
    assert "explicit_authorization_required" in LOCAL_TEST_DB_RESET_RULES
    assert "local_test_database_only" in LOCAL_TEST_DB_RESET_RULES
    assert "docker_compose_down_v_allowed_only_for_disposable_local_db" in (
        LOCAL_TEST_DB_RESET_RULES
    )
    assert "use_alembic_console_command" in LOCAL_TEST_DB_RESET_RULES


def test_policy_blocks_operational_data_flows() -> None:
    assert "block_seed_rebuild_real_import_and_production" in LOCAL_TEST_DB_RESET_RULES
