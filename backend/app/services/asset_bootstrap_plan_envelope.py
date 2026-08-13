"""Envelope versionado do planejamento read-only de bootstrap de ativos."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.asset_bootstrap_contracts import AssetBootstrapReport


@dataclass(frozen=True)
class AssetBootstrapPlanEnvelope:
    report: AssetBootstrapReport

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "asset-bootstrap-plan.v1",
            "mode": "plan",
            "dry_run": True,
            "read_only": True,
            "writes_executed": False,
            "report": self.report.to_dict(),
        }
