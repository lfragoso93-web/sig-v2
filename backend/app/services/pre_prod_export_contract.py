"""Contrato versionado da exportação auditável pré-produção.

Este módulo contém somente estruturas de dados e validações. Ele não acessa o
banco, não lê nem escreve artefatos e não executa SQL.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

EXPORT_MANIFEST_SCHEMA_VERSION = "pre-prod-export.v1"
EXPORT_FORMAT = "csv"
EXPORT_CLASSIFICATION = "export_before_cleanup"

ExportClassification = Literal["export_before_cleanup"]
ExportFormat = Literal["csv"]


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


@dataclass(frozen=True)
class ExportColumn:
    name: str
    postgres_type: str
    nullable: bool
    ordinal_position: int

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("column name is required")
        if not self.postgres_type.strip():
            raise ValueError("postgres_type is required")
        if self.ordinal_position < 1:
            raise ValueError("ordinal_position must be positive")


@dataclass(frozen=True)
class ExportTableArtifact:
    table_name: str
    classification: ExportClassification
    row_count: int
    relative_path: str
    format: ExportFormat
    byte_size: int
    data_sha256: str
    schema_sha256: str
    columns: list[ExportColumn]

    def __post_init__(self) -> None:
        if not self.table_name.strip():
            raise ValueError("table_name is required")
        if self.classification != EXPORT_CLASSIFICATION:
            raise ValueError("only export_before_cleanup tables may be exported")
        if self.row_count < 0:
            raise ValueError("row_count cannot be negative")
        if self.byte_size < 0:
            raise ValueError("byte_size cannot be negative")
        if self.format != EXPORT_FORMAT:
            raise ValueError(f"unsupported export format: {self.format!r}")
        if not self.relative_path.strip() or self.relative_path.startswith(("/", "\\")):
            raise ValueError("relative_path must be a non-empty relative path")
        if ".." in self.relative_path.replace("\\", "/").split("/"):
            raise ValueError("relative_path cannot traverse parent directories")
        if not self.columns:
            raise ValueError("exported table must include column metadata")
        names = [column.name for column in self.columns]
        ordinals = [column.ordinal_position for column in self.columns]
        if len(names) != len(set(names)):
            raise ValueError("column names must be unique per table")
        if sorted(ordinals) != list(range(1, len(ordinals) + 1)):
            raise ValueError("column ordinals must be contiguous and start at 1")
        _validate_sha256(self.data_sha256, "data_sha256")
        _validate_sha256(self.schema_sha256, "schema_sha256")


@dataclass(frozen=True)
class ExportSourceSnapshot:
    transaction_isolation: str
    read_only: bool
    cleanup_impact_schema_version: str
    cleanup_impact_sha256: str
    inventory_schema_version: str
    exported_tables: list[str]

    def __post_init__(self) -> None:
        if self.transaction_isolation != "repeatable read":
            raise ValueError("export must use repeatable read isolation")
        if not self.read_only:
            raise ValueError("export source transaction must be read-only")
        if self.cleanup_impact_schema_version != "pre-prod-cleanup-impact.v2":
            raise ValueError("unsupported cleanup impact schema")
        if self.inventory_schema_version != "pre-prod-inventory.v2":
            raise ValueError("unsupported inventory schema")
        if not self.exported_tables:
            raise ValueError("snapshot must declare exported tables")
        if len(self.exported_tables) != len(set(self.exported_tables)):
            raise ValueError("snapshot exported tables must be unique")
        _validate_sha256(self.cleanup_impact_sha256, "cleanup_impact_sha256")


@dataclass(frozen=True)
class ExportSafety:
    source_read_only: bool = True
    source_writes_executed: int = 0
    cleanup_executed: bool = False
    rebuild_executed: bool = False
    overwrite_performed: bool = False

    def __post_init__(self) -> None:
        if not self.source_read_only:
            raise ValueError("export must be read-only at the source")
        if self.source_writes_executed != 0:
            raise ValueError("export cannot record source database writes")
        if self.cleanup_executed or self.rebuild_executed:
            raise ValueError("export cannot execute cleanup or rebuild")
        if self.overwrite_performed:
            raise ValueError("export cannot overwrite existing artifacts")


@dataclass(frozen=True)
class PreProdExportManifest:
    schema_version: str
    generated_at: str
    run_id: str
    branch: str
    commit_sha: str
    source: ExportSourceSnapshot
    tables: list[ExportTableArtifact]
    safety: ExportSafety

    def __post_init__(self) -> None:
        if self.schema_version != EXPORT_MANIFEST_SCHEMA_VERSION:
            raise ValueError(f"unsupported export manifest schema: {self.schema_version!r}")
        if not self.generated_at.strip():
            raise ValueError("generated_at is required")
        if not self.run_id.strip():
            raise ValueError("run_id is required")
        if not self.branch.strip():
            raise ValueError("branch is required")
        _validate_commit_sha(self.commit_sha)
        if not self.tables:
            raise ValueError("manifest must include at least one exported table")

        table_names = [table.table_name for table in self.tables]
        paths = [table.relative_path for table in self.tables]
        if len(table_names) != len(set(table_names)):
            raise ValueError("manifest table names must be unique")
        if len(paths) != len(set(paths)):
            raise ValueError("manifest artifact paths must be unique")
        if set(table_names) != set(self.source.exported_tables):
            raise ValueError("manifest tables must match source snapshot export gate")

    @property
    def total_rows(self) -> int:
        return sum(table.row_count for table in self.tables)

    @property
    def total_bytes(self) -> int:
        return sum(table.byte_size for table in self.tables)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["totals"] = {
            "tables": len(self.tables),
            "rows": self.total_rows,
            "bytes": self.total_bytes,
        }
        return payload
