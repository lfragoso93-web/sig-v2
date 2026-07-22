"""Contrato versionado da fundação segura da limpeza pré-produção.

Este módulo contém somente estruturas de dados e validações. Ele não acessa o
banco, não lê nem escreve artefatos e não executa SQL.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import PurePosixPath
from typing import Any, Literal

CLEANUP_EXECUTION_SCHEMA_VERSION = "pre-prod-cleanup-execution.v1"
CLEANUP_EXECUTION_MODE = "plan"
CLEANUP_BRANCH = "stable-15jun"

ArtifactKind = Literal["cleanup_impact", "export_manifest", "export_table"]
TableClassification = Literal["export_before_cleanup", "rebuildable"]


def _validate_sha256(value: str, field_name: str) -> None:
    if len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value.lower()
    ):
        raise ValueError(f"{field_name} must be a 64-character hexadecimal SHA-256")


def _validate_commit_sha(value: str) -> None:
    if len(value) != 40 or any(
        character not in "0123456789abcdef" for character in value.lower()
    ):
        raise ValueError("commit_sha must be a full 40-character hexadecimal SHA")


def _validate_relative_path(value: str) -> None:
    path = PurePosixPath(value)
    if not value.strip() or path.is_absolute() or ".." in path.parts:
        raise ValueError("relative_path must be a safe non-empty relative path")


@dataclass(frozen=True)
class CleanupExecutionArtifact:
    kind: ArtifactKind
    schema_version: str
    relative_path: str
    sha256: str

    def __post_init__(self) -> None:
        if self.kind not in {"cleanup_impact", "export_manifest", "export_table"}:
            raise ValueError(f"unsupported artifact kind: {self.kind!r}")
        if not self.schema_version.strip():
            raise ValueError("artifact schema_version is required")
        _validate_relative_path(self.relative_path)
        _validate_sha256(self.sha256, "artifact sha256")


@dataclass(frozen=True)
class CleanupExecutionTable:
    name: str
    classification: TableClassification
    expected_rows_before: int
    cleanup_position: int

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("table name is required")
        if self.classification not in {"export_before_cleanup", "rebuildable"}:
            raise ValueError(f"unsupported cleanup classification: {self.classification!r}")
        if self.expected_rows_before < 0:
            raise ValueError("expected_rows_before cannot be negative")
        if self.cleanup_position < 1:
            raise ValueError("cleanup_position must be positive")


@dataclass(frozen=True)
class CleanupExecutionSafety:
    plan_only: bool = True
    database_writes_executed: int = 0
    cleanup_executed: bool = False
    rebuild_executed: bool = False
    artifact_overwrite_performed: bool = False
    reusable_run_id: bool = False

    def __post_init__(self) -> None:
        if not self.plan_only:
            raise ValueError("cleanup execution foundation must remain plan-only")
        if self.database_writes_executed != 0:
            raise ValueError("plan-only contract cannot record database writes")
        if self.cleanup_executed or self.rebuild_executed:
            raise ValueError("plan-only contract cannot execute cleanup or rebuild")
        if self.artifact_overwrite_performed:
            raise ValueError("cleanup execution artifacts cannot be overwritten")
        if self.reusable_run_id:
            raise ValueError("cleanup execution run_id cannot be reusable")


@dataclass(frozen=True)
class PreProdCleanupExecutionPlan:
    schema_version: str
    generated_at: str
    mode: str
    run_id: str
    branch: str
    commit_sha: str
    cleanup_impact_sha256: str
    export_manifest_sha256: str
    artifacts: list[CleanupExecutionArtifact]
    tables: list[CleanupExecutionTable]
    cleanup_order: list[str]
    blockers: list[str]
    safety: CleanupExecutionSafety

    def __post_init__(self) -> None:
        if self.schema_version != CLEANUP_EXECUTION_SCHEMA_VERSION:
            raise ValueError(f"unsupported cleanup execution schema: {self.schema_version!r}")
        if self.mode != CLEANUP_EXECUTION_MODE:
            raise ValueError(f"unsupported cleanup execution mode: {self.mode!r}")
        if not self.generated_at.strip():
            raise ValueError("generated_at is required")
        if not self.run_id.strip() or PurePosixPath(self.run_id).name != self.run_id:
            raise ValueError("run_id must be a safe non-empty name")
        if self.branch != CLEANUP_BRANCH:
            raise ValueError("cleanup execution must target stable-15jun")
        _validate_commit_sha(self.commit_sha)
        _validate_sha256(self.cleanup_impact_sha256, "cleanup_impact_sha256")
        _validate_sha256(self.export_manifest_sha256, "export_manifest_sha256")

        if self.blockers:
            raise ValueError("approved cleanup execution plan cannot contain blockers")
        if not self.artifacts:
            raise ValueError("cleanup execution plan must include approved artifacts")
        if not self.tables:
            raise ValueError("cleanup execution plan must include cleanup tables")

        artifact_paths = [artifact.relative_path for artifact in self.artifacts]
        if len(artifact_paths) != len(set(artifact_paths)):
            raise ValueError("artifact paths must be unique")
        required_kinds = {"cleanup_impact", "export_manifest"}
        artifact_kinds = {artifact.kind for artifact in self.artifacts}
        if not required_kinds.issubset(artifact_kinds):
            raise ValueError("cleanup impact and export manifest artifacts are required")

        table_names = [table.name for table in self.tables]
        positions = [table.cleanup_position for table in self.tables]
        if len(table_names) != len(set(table_names)):
            raise ValueError("cleanup tables must be unique")
        if sorted(positions) != list(range(1, len(positions) + 1)):
            raise ValueError("cleanup positions must be contiguous and start at 1")
        expected_order = [
            table.name for table in sorted(self.tables, key=lambda item: item.cleanup_position)
        ]
        if self.cleanup_order != expected_order:
            raise ValueError("cleanup_order must match table cleanup positions")

        export_tables = {
            table.name
            for table in self.tables
            if table.classification == "export_before_cleanup"
        }
        export_artifacts = {
            PurePosixPath(artifact.relative_path).stem
            for artifact in self.artifacts
            if artifact.kind == "export_table"
        }
        if export_artifacts != export_tables:
            raise ValueError("export table artifacts must match export-before-cleanup tables")

    @property
    def expected_rows_before(self) -> int:
        return sum(table.expected_rows_before for table in self.tables)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["totals"] = {
            "artifacts": len(self.artifacts),
            "tables": len(self.tables),
            "expected_rows_before": self.expected_rows_before,
        }
        return payload
