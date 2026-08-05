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

    def to_dict(self) -> dict[str, object]:
        return {
            "ticker": self.ticker,
            "asset_type": self.asset_type,
            "ok": self.ok,
            "capabilities": [item.to_dict() for item in self.capabilities],
            "coverage": self.coverage.to_dict(),
        }


class AssetBootstrapCapability(Protocol):
    name: AssetBootstrapCapabilityName

    async def execute(
        self,
        request: AssetBootstrapRequest,
    ) -> AssetBootstrapCapabilityResult:
        """Executa uma capacidade isolada sem assumir provider ou transação."""
