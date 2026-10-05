"""Fail-closed identity contract for the local synthetic portfolio seed."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.certification.portfolio_synthetic_fixture import (
    EXPECTED_ENVIRONMENT,
    ISSUE_NUMBER,
    SCHEMA_VERSION,
    load_portfolio_synthetic_certification_fixture,
)


SYNTHETIC_USER_EMAIL = "portfolio-certification-303@example.com"
SYNTHETIC_USER_NAME = "SGI Portfolio Certification #303"
SYNTHETIC_PORTFOLIO_NAME = "PORTFOLIO-TEST-READY synthetic multiclasse"
SYNTHETIC_OWNERSHIP_MARKER = "sgi:certification:issue-303:v1"


class SyntheticSeedContractError(ValueError):
    """Raised when synthetic seed ownership or fixture safety cannot be proven."""


@dataclass(frozen=True)
class SyntheticSeedIdentity:
    schema_version: str
    issue_number: int
    user_email: str
    user_name: str
    portfolio_name: str
    ownership_marker: str


def _require_exact_fixture_contract(fixture: dict[str, Any]) -> None:
    if fixture.get("schema_version") != SCHEMA_VERSION:
        raise SyntheticSeedContractError("unsupported synthetic certification schema")
    if fixture.get("issue") != ISSUE_NUMBER:
        raise SyntheticSeedContractError("synthetic certification must reference issue #303")
    if fixture.get("environment") != EXPECTED_ENVIRONMENT:
        raise SyntheticSeedContractError("synthetic certification environment is not safe")


def load_synthetic_seed_identity() -> SyntheticSeedIdentity:
    """Return deterministic identity only after the canonical fixture passes safety gates."""
    fixture = load_portfolio_synthetic_certification_fixture()
    _require_exact_fixture_contract(fixture)
    return SyntheticSeedIdentity(
        schema_version=SCHEMA_VERSION,
        issue_number=ISSUE_NUMBER,
        user_email=SYNTHETIC_USER_EMAIL,
        user_name=SYNTHETIC_USER_NAME,
        portfolio_name=SYNTHETIC_PORTFOLIO_NAME,
        ownership_marker=SYNTHETIC_OWNERSHIP_MARKER,
    )


def assert_synthetic_ownership(marker: str | None) -> None:
    """Authorize destructive seed operations only for the exact synthetic marker."""
    if marker != SYNTHETIC_OWNERSHIP_MARKER:
        raise SyntheticSeedContractError(
            "synthetic ownership could not be proven; destructive operation refused"
        )
