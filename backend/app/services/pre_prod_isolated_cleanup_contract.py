"""Contratos e validações puras para autorizar limpeza controlada.

Este módulo não acessa banco, arquivos, variáveis de ambiente ou rede. Ele apenas
valida identidades e a confirmação explícita que antecedem o executor
transacional das Issues #196 e #199.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping

ISOLATED_CLEANUP_REPORT_SCHEMA_VERSION = "pre-prod-isolated-cleanup.v1"
APPROVED_PLAN_SCHEMA_VERSION = "pre-prod-cleanup-execution.v1"
APPROVED_PLAN_MODE = "plan"
APPROVED_BRANCH = "stable-15jun"
REQUIRED_ISOLATION_MARKER = "sgi-pre-prod-isolated"
REQUIRED_PRE_PROD_MARKER = "sgi-pre-prod-real"
SUPPORTED_TARGET_MARKERS = frozenset(
    {REQUIRED_ISOLATION_MARKER, REQUIRED_PRE_PROD_MARKER}
)


class IsolatedCleanupValidationError(ValueError):
    """Falha fechada de validação anterior a qualquer escrita."""


def _validate_sha256(value: str, field_name: str) -> str:
    normalized = value.lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise IsolatedCleanupValidationError(
            f"{field_name} must be a 64-character hexadecimal SHA-256"
        )
    return normalized


def _validate_commit_sha(value: str) -> str:
    normalized = value.lower()
    if len(normalized) != 40 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise IsolatedCleanupValidationError(
            "commit_sha must be a full 40-character hexadecimal SHA"
        )
    return normalized


def canonical_json_sha256(payload: Mapping[str, Any]) -> str:
    """Calcula SHA-256 determinístico sem depender da formatação do arquivo."""
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class CleanupDatabaseIdentity:
    host: str
    port: int
    database: str
    isolation_marker: str | None = None

    def __post_init__(self) -> None:
        if not self.host.strip():
            raise IsolatedCleanupValidationError("database host is required")
        if not 1 <= self.port <= 65535:
            raise IsolatedCleanupValidationError("database port must be between 1 and 65535")
        if not self.database.strip():
            raise IsolatedCleanupValidationError("database name is required")

    @property
    def normalized_key(self) -> tuple[str, int, str]:
        return (self.host.strip().lower(), self.port, self.database.strip().lower())

    @property
    def redacted_label(self) -> str:
        return f"{self.host.strip().lower()}:{self.port}/{self.database.strip()}"


@dataclass(frozen=True)
class CleanupExecutionConfirmation:
    run_id: str
    target_database: str
    commit_sha: str
    plan_sha256: str
    confirmation: str

    def __post_init__(self) -> None:
        if not self.run_id.strip() or "/" in self.run_id or "\\" in self.run_id:
            raise IsolatedCleanupValidationError("run_id must be a safe non-empty name")
        if not self.target_database.strip():
            raise IsolatedCleanupValidationError("target_database is required")
        object.__setattr__(self, "commit_sha", _validate_commit_sha(self.commit_sha))
        object.__setattr__(self, "plan_sha256", _validate_sha256(self.plan_sha256, "plan_sha256"))
        if self.confirmation != self.expected_confirmation:
            raise IsolatedCleanupValidationError("composite cleanup confirmation does not match")

    @property
    def expected_confirmation(self) -> str:
        return (
            f"CLEANUP {self.run_id} ON {self.target_database} "
            f"AT {self.commit_sha} WITH {self.plan_sha256}"
        )


@dataclass(frozen=True)
class ApprovedCleanupPlanIdentity:
    run_id: str
    branch: str
    commit_sha: str
    plan_sha256: str
    cleanup_order: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise IsolatedCleanupValidationError("plan run_id is required")
        if self.branch != APPROVED_BRANCH:
            raise IsolatedCleanupValidationError("cleanup plan must target stable-15jun")
        object.__setattr__(self, "commit_sha", _validate_commit_sha(self.commit_sha))
        object.__setattr__(self, "plan_sha256", _validate_sha256(self.plan_sha256, "plan_sha256"))
        if not self.cleanup_order:
            raise IsolatedCleanupValidationError("cleanup plan must contain cleanup_order")
        if len(self.cleanup_order) != len(set(self.cleanup_order)):
            raise IsolatedCleanupValidationError("cleanup_order must contain unique tables")


@dataclass(frozen=True)
class IsolatedCleanupAuthorization:
    schema_version: str
    plan: ApprovedCleanupPlanIdentity
    source: CleanupDatabaseIdentity
    target: CleanupDatabaseIdentity
    confirmation: CleanupExecutionConfirmation

    def __post_init__(self) -> None:
        if self.schema_version != ISOLATED_CLEANUP_REPORT_SCHEMA_VERSION:
            raise IsolatedCleanupValidationError(
                f"unsupported isolated cleanup schema: {self.schema_version!r}"
            )
        if self.target.isolation_marker not in SUPPORTED_TARGET_MARKERS:
            raise IsolatedCleanupValidationError(
                "cleanup target is missing a supported execution marker"
            )
        same_database = self.source.normalized_key == self.target.normalized_key
        if self.target.isolation_marker == REQUIRED_ISOLATION_MARKER and same_database:
            raise IsolatedCleanupValidationError(
                "isolated cleanup target must be different from the source database"
            )
        if self.target.isolation_marker == REQUIRED_PRE_PROD_MARKER and not same_database:
            raise IsolatedCleanupValidationError(
                "real pre-production cleanup must target the source database identity"
            )
        if self.confirmation.run_id != self.plan.run_id:
            raise IsolatedCleanupValidationError("confirmation run_id differs from plan")
        if self.confirmation.target_database != self.target.database:
            raise IsolatedCleanupValidationError(
                "confirmation target database differs from cleanup target"
            )
        if self.confirmation.commit_sha != self.plan.commit_sha:
            raise IsolatedCleanupValidationError("confirmation commit_sha differs from plan")
        if self.confirmation.plan_sha256 != self.plan.plan_sha256:
            raise IsolatedCleanupValidationError("confirmation plan_sha256 differs from plan")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source"] = {"database": self.source.redacted_label}
        payload["target"] = {
            "database": self.target.redacted_label,
            "isolation_marker": self.target.isolation_marker,
        }
        payload["confirmation"].pop("confirmation", None)
        return payload


def validate_approved_plan(
    *,
    payload: Mapping[str, Any],
    expected_run_id: str,
    expected_commit_sha: str,
    expected_plan_sha256: str,
) -> ApprovedCleanupPlanIdentity:
    """Revalida identidade e invariantes do plano sem executar I/O."""
    actual_sha256 = canonical_json_sha256(payload)
    normalized_expected_sha = _validate_sha256(expected_plan_sha256, "expected_plan_sha256")
    if actual_sha256 != normalized_expected_sha:
        raise IsolatedCleanupValidationError("cleanup plan checksum differs from approved checksum")

    if payload.get("schema_version") != APPROVED_PLAN_SCHEMA_VERSION:
        raise IsolatedCleanupValidationError("unsupported cleanup plan schema_version")
    if payload.get("mode") != APPROVED_PLAN_MODE:
        raise IsolatedCleanupValidationError("cleanup plan must remain in plan mode")
    if payload.get("branch") != APPROVED_BRANCH:
        raise IsolatedCleanupValidationError("cleanup plan branch differs from stable-15jun")
    if payload.get("blockers"):
        raise IsolatedCleanupValidationError("cleanup plan contains blockers")

    run_id = str(payload.get("run_id", ""))
    if run_id != expected_run_id:
        raise IsolatedCleanupValidationError("cleanup plan run_id differs from requested run")

    commit_sha = _validate_commit_sha(str(payload.get("commit_sha", "")))
    normalized_expected_commit = _validate_commit_sha(expected_commit_sha)
    if commit_sha != normalized_expected_commit:
        raise IsolatedCleanupValidationError("cleanup plan commit_sha differs from approved commit")

    cleanup_order_value = payload.get("cleanup_order")
    if not isinstance(cleanup_order_value, list) or not all(
        isinstance(table, str) and table.strip() for table in cleanup_order_value
    ):
        raise IsolatedCleanupValidationError("cleanup_order must be a non-empty string list")

    safety = payload.get("safety")
    if not isinstance(safety, Mapping):
        raise IsolatedCleanupValidationError("cleanup plan safety section is required")
    if safety.get("plan_only") is not True:
        raise IsolatedCleanupValidationError("approved cleanup plan must be plan-only")
    if safety.get("database_writes_executed") != 0:
        raise IsolatedCleanupValidationError("approved cleanup plan records database writes")
    if safety.get("cleanup_executed") is not False:
        raise IsolatedCleanupValidationError("approved cleanup plan already records cleanup")
    if safety.get("rebuild_executed") is not False:
        raise IsolatedCleanupValidationError("approved cleanup plan already records rebuild")

    return ApprovedCleanupPlanIdentity(
        run_id=run_id,
        branch=APPROVED_BRANCH,
        commit_sha=commit_sha,
        plan_sha256=actual_sha256,
        cleanup_order=tuple(cleanup_order_value),
    )
