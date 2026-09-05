import pytest

from app.certification import portfolio_seed_contract as contract


def test_synthetic_seed_identity_is_deterministic_and_safe() -> None:
    identity = contract.load_synthetic_seed_identity()

    assert identity.schema_version == "portfolio-synthetic-certification.v1"
    assert identity.issue_number == 303
    assert identity.user_email.endswith("@synthetic.invalid")
    assert identity.user_name == "SGI Portfolio Certification #303"
    assert identity.portfolio_name == "PORTFOLIO-TEST-READY synthetic multiclasse"
    assert identity.ownership_marker == "sgi:certification:issue-303:v1"


def test_assert_synthetic_ownership_accepts_only_exact_marker() -> None:
    contract.assert_synthetic_ownership("sgi:certification:issue-303:v1")

    for marker in (None, "", "sgi:certification:issue-303", "real-data"):
        with pytest.raises(
            contract.SyntheticSeedContractError,
            match="ownership could not be proven",
        ):
            contract.assert_synthetic_ownership(marker)


def test_seed_contract_rejects_environment_that_allows_real_data() -> None:
    fixture = {
        "schema_version": contract.SCHEMA_VERSION,
        "issue": contract.ISSUE_NUMBER,
        "environment": {
            "test_ready": True,
            "ready_for_real_data": True,
            "real_data_allowed": True,
        },
    }

    with pytest.raises(
        contract.SyntheticSeedContractError,
        match="environment is not safe",
    ):
        contract._require_exact_fixture_contract(fixture)


def test_seed_contract_rejects_wrong_schema_or_issue() -> None:
    safe_environment = dict(contract.EXPECTED_ENVIRONMENT)

    with pytest.raises(
        contract.SyntheticSeedContractError,
        match="unsupported synthetic certification schema",
    ):
        contract._require_exact_fixture_contract(
            {
                "schema_version": "portfolio-synthetic-certification.v2",
                "issue": contract.ISSUE_NUMBER,
                "environment": safe_environment,
            }
        )

    with pytest.raises(
        contract.SyntheticSeedContractError,
        match="must reference issue #303",
    ):
        contract._require_exact_fixture_contract(
            {
                "schema_version": contract.SCHEMA_VERSION,
                "issue": 999,
                "environment": safe_environment,
            }
        )
