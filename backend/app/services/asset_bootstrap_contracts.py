"""Contratos neutros do bootstrap canônico de ativos."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Protocol


class AssetBootstrapCapabilityName(str, Enum):
    CATALOG = "catalog"
    QUOTES = "quotes"
    INCOME_EVENTS = "income_events"
    CORPORATE_EVENTS = "corporate_events"
    COVERAGE = "coverage"


class AssetBootstrapStageState(str, Enum):
    PLANNED = "planned"
    EXECUTED = "executed"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass(frozen=True)
class AssetBootstrapExecutionIdentity:
    run_id: str
    branch: str
    commit_sha: str

    def normalized(self) -> "AssetBootstrapExecutionIdentity":
        run_id = self.run_id.strip()
        branch = self.branch.strip()
        commit_sha = self.commit_sha.strip().lower()
        if not run_id:
            raise ValueError("run_id is required")
        if not branch:
            raise ValueError("branch is required")
        if not commit_sha:
            raise ValueError("commit_sha is required")
        return AssetBootstrapExecutionIdentity(
            run_id=run_id,
            branch=branch,
            commit_sha=commit_sha,
        )

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class AssetBootstrapRequest:
    ticker: str
    asset_type: str


@dataclass(frozen=True)
class AssetBootstrapCapabilityResult:
    capability: AssetBootstrapCapabilityName
    ok: bool
    state: AssetBootstrapStageState = AssetBootstrapStageState.EXECUTED
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["capability"] = self.capability.value
        payload["state"] = self.state.value
        return payload


@dataclass(frozen=True)
class AssetBootstrapCoverageSummary:
    total_capabilities: int
    successful_capabilities: int
    failed_capabilities: tuple[str, ...]
    blocked_capabilities: tuple[str, ...]
    created: int
    updated: int
    unchanged: int
    warnings: int
    errors: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class AssetBootstrapReport:
    ticker: str
    asset_type: str
    ok: bool
    capabilities: tuple[AssetBootstrapCapabilityResult, ...]
    coverage: AssetBootstrapCoverageSummary
    identity: AssetBootstrapExecutionIdentity | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "ticker": self.ticker,
            "asset_type": self.asset_type,
            "ok": self.ok,
            "capabilities": [item.to_dict() for item in self.capabilities],
            "coverage": self.coverage.to_dict(),
        }
        if self.identity is not None:
            payload["identity"] = self.identity.to_dict()
        return payload


class AssetBootstrapCapability(Protocol):
    name: AssetBootstrapCapabilityName

    async def execute(
        self,
        request: AssetBootstrapRequest,
    ) -> AssetBootstrapCapabilityResult:
        """Executa uma capacidade isolada sem assumir provider ou transação."""
