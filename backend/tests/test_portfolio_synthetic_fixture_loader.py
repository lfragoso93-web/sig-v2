import json

import pytest

from app.certification import portfolio_synthetic_fixture


def _write_fixture(tmp_path, fixture: object):
    path = tmp_path / "portfolio_synthetic_certification_v1.json"
    path.write_text(json.dumps(fixture), encoding="utf-8")
    return path


def _safe_fixture() -> dict:
    return {
        "schema_version": "portfolio-synthetic-certification.v1",
        "issue": 303,
        "environment": {
            "test_ready": True,
            "ready_for_real_data": False,
            "real_data_allowed": False,
        },
    }


def test_loader_reads_runtime_fixture() -> None:
    fixture = portfolio_synthetic_fixture.load_portfolio_synthetic_certification_fixture()

    assert fixture["schema_version"] == "portfolio-synthetic-certification.v1"
    assert fixture["issue"] == 303
    assert fixture["environment"]["test_ready"] is True
    assert fixture["environment"]["ready_for_real_data"] is False
    assert fixture["environment"]["real_data_allowed"] is False


def test_loader_rejects_unsupported_schema(tmp_path, monkeypatch) -> None:
    fixture = _safe_fixture()
    fixture["schema_version"] = "portfolio-synthetic-certification.v999"
    monkeypatch.setattr(
        portfolio_synthetic_fixture,
        "FIXTURE_PATH",
        _write_fixture(tmp_path, fixture),
    )

    with pytest.raises(ValueError, match="unsupported synthetic certification schema"):
        portfolio_synthetic_fixture.load_portfolio_synthetic_certification_fixture()


def test_loader_rejects_wrong_issue(tmp_path, monkeypatch) -> None:
    fixture = _safe_fixture()
    fixture["issue"] = 999
    monkeypatch.setattr(
        portfolio_synthetic_fixture,
        "FIXTURE_PATH",
        _write_fixture(tmp_path, fixture),
    )

    with pytest.raises(ValueError, match="must reference issue #303"):
        portfolio_synthetic_fixture.load_portfolio_synthetic_certification_fixture()


def test_loader_rejects_unsafe_environment(tmp_path, monkeypatch) -> None:
    fixture = _safe_fixture()
    fixture["environment"]["ready_for_real_data"] = True
    monkeypatch.setattr(
        portfolio_synthetic_fixture,
        "FIXTURE_PATH",
        _write_fixture(tmp_path, fixture),
    )

    with pytest.raises(ValueError, match="environment is not safe"):
        portfolio_synthetic_fixture.load_portfolio_synthetic_certification_fixture()


def test_loader_rejects_non_object_json(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        portfolio_synthetic_fixture,
        "FIXTURE_PATH",
        _write_fixture(tmp_path, []),
    )

    with pytest.raises(ValueError, match="must be a JSON object"):
        portfolio_synthetic_fixture.load_portfolio_synthetic_certification_fixture()
