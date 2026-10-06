"""Versioned, fail-closed contract for a read-only certification proof."""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.services.real_data_certification_reader import (
    RealDataCertificationIdentity,
    RealDataCertificationState,
)

CERTIFICATION_PROOF_CONTRACT = "sgi-certification.v1"
CERTIFICATION_TESTS_CONTRACT = "sgi-certification-tests.v1"
_SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
_IDENTIFIER_PATTERN = re.compile(r"[a-z0-9][a-z0-9_.-]{0,79}")


class ProofStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class ServiceStatus(StrEnum):
    HEALTHY = "healthy"
    UNAVAILABLE = "unavailable"


class TestSuiteEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    status: ProofStatus
    required: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not _IDENTIFIER_PATTERN.fullmatch(value):
            raise ValueError("suite name must be a safe identifier")
        return value


class TestEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract: str
    suites: tuple[TestSuiteEvidence, ...]

    @model_validator(mode="after")
    def validate_contract(self) -> TestEvidence:
        if self.contract != CERTIFICATION_TESTS_CONTRACT:
            raise ValueError("unsupported test evidence contract")
        if not self.suites:
            raise ValueError("at least one test suite is required")
        names = [suite.name for suite in self.suites]
        if len(names) != len(set(names)):
            raise ValueError("test suite names must be unique")
        return self


class DoctorFindingEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    finding_id: str
    status: ProofStatus


class ArchitectureEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract: str = "architecture-doctor.v1"
    exit_code: int
    findings: tuple[DoctorFindingEvidence, ...]


class ServiceEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: ServiceStatus
    required: bool


class RuntimeEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    backend: ServiceEvidence
    postgres: ServiceEvidence
    redis: ServiceEvidence


class CertificationEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: str
    ready_for_real_data: bool
    event_id: int | None
    event_key: str | None


class IdentityEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    environment: str
    branch: str
    checkout_sha: str
    runtime_sha: str
    dataset_reference: str
    alembic_revision: str
    gate_issue_reference: str
    pull_request_reference: str

    @field_validator("checkout_sha", "runtime_sha")
    @classmethod
    def validate_sha(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not _SHA_PATTERN.fullmatch(normalized):
            raise ValueError(
                "SHA must contain 40 lowercase hexadecimal characters"
            )
        return normalized


def _collect_failures(
    *,
    identity: IdentityEvidence,
    tests: TestEvidence,
    architecture: ArchitectureEvidence,
    runtime: RuntimeEvidence,
    certification: CertificationEvidence,
) -> tuple[str, ...]:
    failures: list[str] = []
    if identity.checkout_sha != identity.runtime_sha:
        failures.append("identity.sha_mismatch")
    if (
        not certification.ready_for_real_data
        or certification.status != "certified"
    ):
        failures.append("certification.not_certified")
    failures.extend(
        f"tests.{suite.name}"
        for suite in tests.suites
        if suite.required and suite.status is not ProofStatus.PASSED
    )
    if architecture.exit_code != 0 or any(
        finding.status is not ProofStatus.PASSED
        for finding in architecture.findings
    ):
        failures.append("architecture.doctor")
    for name in ("backend", "postgres", "redis"):
        service = getattr(runtime, name)
        if service.required and service.status is not ServiceStatus.HEALTHY:
            failures.append(f"runtime.{name}")
    return tuple(failures)


class CertificationProof(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract: str = CERTIFICATION_PROOF_CONTRACT
    generated_at_utc: datetime
    volatile_fields: tuple[str, ...] = ("generated_at_utc",)
    identity: IdentityEvidence
    tests: TestEvidence
    architecture: ArchitectureEvidence
    runtime: RuntimeEvidence
    certification: CertificationEvidence
    disabled_optional_gates: tuple[str, ...] = ()
    database_writes_executed: int = Field(default=0, ge=0, le=0)
    failures: tuple[str, ...]
    result: ProofStatus

    @field_validator("generated_at_utc")
    @classmethod
    def validate_generated_at_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("generated_at_utc must be timezone-aware")
        if value.utcoffset().total_seconds() != 0:
            raise ValueError("generated_at_utc must use UTC")
        return value

    @field_validator("disabled_optional_gates")
    @classmethod
    def validate_disabled_optional_gates(
        cls,
        values: tuple[str, ...],
    ) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise ValueError("disabled optional gates must be unique")
        if any(not _IDENTIFIER_PATTERN.fullmatch(value) for value in values):
            raise ValueError(
                "disabled optional gate must be a safe identifier"
            )
        return values

    @model_validator(mode="after")
    def validate_semantics(self) -> CertificationProof:
        if self.contract != CERTIFICATION_PROOF_CONTRACT:
            raise ValueError("unsupported certification proof contract")
        expected_failures = _collect_failures(
            identity=self.identity,
            tests=self.tests,
            architecture=self.architecture,
            runtime=self.runtime,
            certification=self.certification,
        )
        if self.failures != expected_failures:
            raise ValueError("failures do not match proof evidence")
        expected_result = (
            ProofStatus.PASSED
            if not expected_failures
            else ProofStatus.FAILED
        )
        if self.result is not expected_result:
            raise ValueError("result does not match proof evidence")
        return self


def build_certification_proof(
    *,
    generated_at_utc: datetime,
    checkout_sha: str,
    identity: RealDataCertificationIdentity,
    certification: RealDataCertificationState,
    tests: TestEvidence,
    architecture: ArchitectureEvidence,
    runtime: RuntimeEvidence,
    disabled_optional_gates: tuple[str, ...] = (),
) -> CertificationProof:
    """Build the proof from allowlisted evidence without performing writes."""

    identity_evidence = IdentityEvidence(
        environment=identity.environment,
        branch=identity.branch,
        checkout_sha=checkout_sha,
        runtime_sha=identity.commit_sha,
        dataset_reference=identity.dataset_reference,
        alembic_revision=identity.alembic_revision,
        gate_issue_reference=identity.gate_issue_reference,
        pull_request_reference=identity.pull_request_reference,
    )
    certification_evidence = CertificationEvidence(
        status=certification.status.value,
        ready_for_real_data=certification.ready_for_real_data,
        event_id=certification.event_id,
        event_key=certification.event_key,
    )
    failures = _collect_failures(
        identity=identity_evidence,
        tests=tests,
        architecture=architecture,
        runtime=runtime,
        certification=certification_evidence,
    )

    return CertificationProof(
        generated_at_utc=generated_at_utc,
        identity=identity_evidence,
        tests=tests,
        architecture=architecture,
        runtime=runtime,
        certification=certification_evidence,
        disabled_optional_gates=disabled_optional_gates,
        failures=failures,
        result=ProofStatus.PASSED if not failures else ProofStatus.FAILED,
    )
