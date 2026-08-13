"""Protege a neutralidade arquitetural do bootstrap canônico de ativos."""

from __future__ import annotations

from pathlib import Path

_SERVICES = Path(__file__).resolve().parents[1] / "app" / "services"
_COORDINATOR = _SERVICES / "asset_bootstrap_coordinator.py"
_CONTRACTS = _SERVICES / "asset_bootstrap_contracts.py"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def test_coordinator_has_no_provider_database_or_orm_dependency() -> None:
    source = _source(_COORDINATOR)

    for forbidden in (
        "sqlalchemy",
        "asyncsession",
        "app.models",
        "brapi",
        "yahoo",
        "requests",
        "httpx",
        ".commit(",
        ".add(",
        ".delete(",
    ):
        assert forbidden not in source


def test_contracts_remain_provider_and_persistence_neutral() -> None:
    source = _source(_CONTRACTS)

    for forbidden in (
        "sqlalchemy",
        "asyncsession",
        "app.models",
        "brapi",
        "yahoo",
        "requests",
        "httpx",
    ):
        assert forbidden not in source
