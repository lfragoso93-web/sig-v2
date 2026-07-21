"""Contrato versionado do dry-run de limpeza pré-produção.

Este módulo contém somente estruturas de dados e validações. Ele não acessa o
banco, não executa SQL e não importa serviços de limpeza ou rebuild.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from app.services.pre_prod_inventory_service import TableInventory

IMPACT_REPORT_SCHEMA_VERSION = "pre-prod-cleanup-impact.v1"
IMPACT_REPORT_MODE = "dry-run"

TableClassification = Literal[
    "preserved",
    "export_before_cleanup",
    "rebuildable",
    "unclassified",
]
ProposedAction = Literal[
    "preserve",
    "export_required",
    "clean_and_rebuild",
    "block",
]

_ACTION_BY_CLASSIFICATION: dict[str, ProposedAction] = {
    "preserved": "preserve",
    "export_before_cleanup": "export_required",
    "rebuildable": "clean_and_rebuild",
    "unclassified": "block",
}


@dataclass(frozen=True)
class CleanupImpactTable:
    name: str
    classification: TableClassification
    proposed_action: ProposedAction
    rationale: str
    row_count: int
    blocked: bool

    @classmethod
    def from_inventory(cls, table: TableInventory) -> "CleanupImpactTable":
        action = _ACTION_BY_CLASSIFICATION.get(table.classification)
        if action is None:
            raise ValueError(
                f"unsupported inventory classification: {table.classification!r}"
            )
        if table.row_count < 0:
            raise ValueError(f"negative row count for table {table.name!r}")

        return cls(
            name=table.name,
            classification=table.classification,  # type: ignore[arg-type]
            proposed_action=action,
            rationale=table.rationale,
            row_count=table.row_count,
            blocked=action == "block",
        )


@dataclass(frozen=True)
class CleanupImpactTotals:
    tables: int
    rows: int
    preserved_tables: int
    export_required_tables: int
    rebuildable_tables: int
    blocked_tables: int

    @classmethod
    def from_tables(cls, tables: list[CleanupImpactTable]) -> "CleanupImpactTotals":
        return cls(
            tables=len(tables),
            rows=sum(table.row_count for table in tables),
            preserved_tables=sum(
                table.proposed_action == "preserve" for table in tables
            ),
            export_required_tables=sum(
                table.proposed_action == "export_required" for table in tables
            ),
            rebuildable_tables=sum(
                table.proposed_action == "clean_and_rebuild" for table in tables
            ),
            blocked_tables=sum(table.blocked for table in tables),
        )


@dataclass(frozen=True)
class CleanupImpactSafety:
    read_only: bool = True
    writes_executed: int = 0
    cleanup_executed: bool = False
    rebuild_executed: bool = False

    def __post_init__(self) -> None:
        if not self.read_only:
            raise ValueError("cleanup impact report must be read-only")
        if self.writes_executed != 0:
            raise ValueError("cleanup impact report cannot record database writes")
        if self.cleanup_executed or self.rebuild_executed:
            raise ValueError("dry-run cannot execute cleanup or rebuild")


@dataclass(frozen=True)
class PreProdCleanupImpactReport:
    schema_version: str
    generated_at: str
    mode: str
    branch: str
    commit_sha: str
    inventory_schema_version: str
    tables: list[CleanupImpactTable]
    totals: CleanupImpactTotals
    blockers: list[str]
    safety: CleanupImpactSafety

    def __post_init__(self) -> None:
        if self.schema_version != IMPACT_REPORT_SCHEMA_VERSION:
            raise ValueError(f"unsupported impact schema: {self.schema_version!r}")
        if self.mode != IMPACT_REPORT_MODE:
            raise ValueError(f"unsupported impact mode: {self.mode!r}")
        if not self.branch.strip():
            raise ValueError("branch is required")
        if len(self.commit_sha) != 40 or any(
            character not in "0123456789abcdef" for character in self.commit_sha.lower()
        ):
            raise ValueError("commit_sha must be a full 40-character hexadecimal SHA")

        expected_totals = CleanupImpactTotals.from_tables(self.tables)
        if self.totals != expected_totals:
            raise ValueError("impact totals do not match table actions")

        blocked_names = sorted(table.name for table in self.tables if table.blocked)
        if sorted(self.blockers) != blocked_names:
            raise ValueError("blockers must match blocked tables")

    @property
    def ok(self) -> bool:
        return not self.blockers

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["ok"] = self.ok
        return payload
