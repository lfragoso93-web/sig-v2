"""CLI read-only para planejar o bootstrap canônico de um ativo."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

from app.services.asset_bootstrap_contracts import (
    AssetBootstrapCapability,
    AssetBootstrapCapabilityName,
    AssetBootstrapCapabilityResult,
    AssetBootstrapExecutionIdentity,
    AssetBootstrapRequest,
)
from app.services.asset_bootstrap_plan_envelope import AssetBootstrapPlanEnvelope
from app.services.asset_bootstrap_planner import plan_asset_bootstrap


@dataclass(frozen=True)
class _PlanningCapability:
    name: AssetBootstrapCapabilityName

    async def execute(
        self,
        request: AssetBootstrapRequest,
    ) -> AssetBootstrapCapabilityResult:
        raise RuntimeError("planning capability must never execute")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ticker")
    parser.add_argument("asset_type")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--commit-sha", required=True)
    args = parser.parse_args()

    capabilities: tuple[AssetBootstrapCapability, ...] = tuple(
        _PlanningCapability(name)
        for name in (
            AssetBootstrapCapabilityName.CATALOG,
            AssetBootstrapCapabilityName.QUOTES,
            AssetBootstrapCapabilityName.INCOME_EVENTS,
            AssetBootstrapCapabilityName.CORPORATE_EVENTS,
            AssetBootstrapCapabilityName.COVERAGE,
        )
    )
    report = plan_asset_bootstrap(
        capabilities,
        AssetBootstrapRequest(
            ticker=args.ticker,
            asset_type=args.asset_type,
        ),
        identity=AssetBootstrapExecutionIdentity(
            run_id=args.run_id,
            branch=args.branch,
            commit_sha=args.commit_sha,
        ),
    )
    print(json.dumps(AssetBootstrapPlanEnvelope(report).to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
