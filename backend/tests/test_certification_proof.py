"""Contract and fail-closed tests for sgi-certification.v1."""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.services.certification_proof import (
    CERTIFICATION_PROOF_CONTRACT,
    ArchitectureEvidence,
    DoctorFindingEvidence,
    ProofStatus,
    RuntimeEvidence,
    ServiceEvidence,
    ServiceStatus,
    TestEvidence as CertificationTestEvidence,
    TestSuiteEvidence as CertificationTestSuiteEvidence,
    build_certification_proof,
)
from app.services.real_data_certification_reader import (
    RealDataCertificationIdentity,
    RealDataCertificationState,
    RealDataCertificationStatus,
)

SHA = "a" * 40


def _identity() -> RealDataCertificationIdentity:
    return RealDataCertificationIdentity(
        environment="local-canonical",
        branch="stable-15jun",
        commit_sha=SHA,
        dataset_reference="pre-prod-backup.v3:sha256:" + "b" * 64,
        alembic_revision="20261005_real_data_certification",
        gate_issue_reference="#227",
        pull_request_reference="#362",
    )


def _tests(
    status: ProofStatus = ProofStatus.PASSED,
) -> CertificationTestEvidence:
    return CertificationTestEvidence(
        contract="sgi-certification-tests.v1",
        suites=(
            CertificationTestSuiteEvidence(name="canonical", status=status),
        ),
    )


def _architecture(
    status: ProofStatus = ProofStatus.PASSED,
) -> ArchitectureEvidence:
    return ArchitectureEvidence(
        exit_code=0 if status is ProofStatus.PASSED else 1,
        findings=(DoctorFindingEvidence(finding_id="SGI001", status=status),),
    )


def _runtime() -> RuntimeEvidence:
    healthy = ServiceEvidence(status=ServiceStatus.HEALTHY, required=True)
    return RuntimeEvidence(
        backend=healthy,
        postgres=healthy,
        redis=ServiceEvidence(
            status=ServiceStatus.UNAVAILABLE,
            required=False,
        ),
    )


def _certification(
    status: RealDataCertificationStatus = (
        RealDataCertificationStatus.CERTIFIED
    ),
) -> RealDataCertificationState:
    return RealDataCertificationState(
        status=status,
        ready_for_real_data=status is RealDataCertificationStatus.CERTIFIED,
        event_id=1,
        event_key="event-key",
    )


def _proof(**overrides):
    values = {
        "generated_at_utc": datetime(2026, 10, 6, tzinfo=timezone.utc),
        "checkout_sha": SHA,
        "identity": _identity(),
        "certification": _certification(),
        "tests": _tests(),
        "architecture": _architecture(),
        "runtime": _runtime(),
    }
    values.update(overrides)
    return build_certification_proof(**values)


def test_passed_proof_has_exact_identity_and_no_secret_fields() -> None:
    proof = _proof()
    payload = proof.model_dump(mode="json")

    assert proof.contract == CERTIFICATION_PROOF_CONTRACT
    assert proof.result is ProofStatus.PASSED
    assert proof.failures == ()
    assert proof.database_writes_executed == 0
    assert payload["volatile_fields"] == ["generated_at_utc"]
    serialized = proof.model_dump_json().lower()
    forbidden_fields = (
        "password",
        "token",
        "connection_string",
        "database_url",
    )
    for forbidden in forbidden_fields:
        assert forbidden not in serialized


@pytest.mark.parametrize(
    ("overrides", "failure"),
    [
        ({"checkout_sha": "b" * 40}, "identity.sha_mismatch"),
        (
            {
                "certification": _certification(
                    RealDataCertificationStatus.REVOKED
                )
            },
            "certification.not_certified",
        ),
        ({"tests": _tests(ProofStatus.FAILED)}, "tests.canonical"),
        (
            {"architecture": _architecture(ProofStatus.FAILED)},
            "architecture.doctor",
        ),
    ],
)
def test_required_failure_prevents_passed(overrides, failure: str) -> None:
    proof = _proof(**overrides)

    assert proof.result is ProofStatus.FAILED
    assert failure in proof.failures


def test_checked_in_contract_rejects_unknown_fields_and_invalid_sha() -> None:
    payload = _proof().model_dump(mode="json")
    payload["secret"] = "must-not-be-accepted"
    with pytest.raises(ValidationError, match="extra_forbidden"):
        type(_proof()).model_validate(payload)

    with pytest.raises(ValidationError, match="40 lowercase hexadecimal"):
        _proof(checkout_sha="short")


def test_schema_rejects_tampered_result_or_failure_list() -> None:
    failed_payload = _proof(checkout_sha="b" * 40).model_dump(mode="json")
    failed_payload["result"] = "passed"
    with pytest.raises(ValidationError, match="result does not match"):
        type(_proof()).model_validate(failed_payload)

    failed_payload = _proof(checkout_sha="b" * 40).model_dump(mode="json")
    failed_payload["failures"] = []
    with pytest.raises(ValidationError, match="failures do not match"):
        type(_proof()).model_validate(failed_payload)


def test_test_evidence_is_allowlisted_and_requires_unique_suites() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        CertificationTestEvidence.model_validate(
            {
                "contract": "sgi-certification-tests.v1",
                "suites": [
                    {
                        "name": "canonical",
                        "status": "passed",
                        "required": True,
                        "output": "could contain secrets",
                    }
                ],
            }
        )
    with pytest.raises(ValidationError, match="must be unique"):
        CertificationTestEvidence(
            contract="sgi-certification-tests.v1",
            suites=(
                CertificationTestSuiteEvidence(
                    name="same", status=ProofStatus.PASSED
                ),
                CertificationTestSuiteEvidence(
                    name="same", status=ProofStatus.PASSED
                ),
            ),
        )


def test_proof_requires_utc_timestamp_and_safe_optional_gate_names() -> None:
    with pytest.raises(ValidationError, match="must use UTC"):
        _proof(
            generated_at_utc=datetime(
                2026,
                10,
                6,
                tzinfo=timezone(timedelta(hours=-3)),
            )
        )
    with pytest.raises(ValidationError, match="safe identifier"):
        _proof(disabled_optional_gates=("TOKEN=secret",))
