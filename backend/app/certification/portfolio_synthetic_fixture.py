import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "portfolio-synthetic-certification.v1"
ISSUE_NUMBER = 303
EXPECTED_ENVIRONMENT = {
    "test_ready": True,
    "ready_for_real_data": False,
    "real_data_allowed": False,
}
FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "portfolio_synthetic_certification_v1.json"
)


def _validate_fixture(fixture: dict[str, Any]) -> None:
    if fixture.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported synthetic certification schema")
    if fixture.get("issue") != ISSUE_NUMBER:
        raise ValueError("synthetic certification fixture must reference issue #303")
    if fixture.get("environment") != EXPECTED_ENVIRONMENT:
        raise ValueError("synthetic certification fixture environment is not safe")


def load_portfolio_synthetic_certification_fixture() -> dict[str, Any]:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    if not isinstance(fixture, dict):
        raise ValueError("synthetic certification fixture must be a JSON object")
    _validate_fixture(fixture)
    return fixture
