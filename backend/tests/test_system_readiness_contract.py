from dataclasses import dataclass

from app.services.system_readiness_service import (
    BootstrapReadinessState,
    get_bootstrap_readiness,
    mark_bootstrap_finished,
    mark_bootstrap_running,
    reset_bootstrap_readiness_for_tests,
)


@dataclass(frozen=True)
class _Stage:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class _Report:
    schema_version: str
    started_at: str
    finished_at: str
    ok: bool
    stages: tuple[_Stage, ...]


def setup_function() -> None:
    reset_bootstrap_readiness_for_tests()


def test_partial_bootstrap_can_complete_without_releasing_real_data() -> None:
    mark_bootstrap_running(schema_version="system-bootstrap.v1", started_at="start")
    report = _Report(
        schema_version="system-bootstrap.v1",
        started_at="start",
        finished_at="end",
        ok=True,
        stages=(_Stage(name="asset_catalog", ok=True, detail="ok"),),
    )
    mark_bootstrap_finished(report, certified_for_real_data=False)

    readiness = get_bootstrap_readiness()
    assert readiness.state is BootstrapReadinessState.READY
    assert readiness.bootstrap_complete is True
    assert readiness.ready_for_real_data is False
    assert readiness.certified_for_real_data is False


def test_failed_bootstrap_never_releases_real_data() -> None:
    mark_bootstrap_running(schema_version="system-bootstrap.v1", started_at="start")
    report = _Report(
        schema_version="system-bootstrap.v1",
        started_at="start",
        finished_at="end",
        ok=False,
        stages=(_Stage(name="asset_catalog", ok=False, detail="failed"),),
    )
    mark_bootstrap_finished(report, certified_for_real_data=True)

    readiness = get_bootstrap_readiness()
    assert readiness.state is BootstrapReadinessState.FAILED
    assert readiness.ready_for_real_data is False
    assert readiness.failed_stage == "asset_catalog"
