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


@dataclass(frozen=True)
class AssetBootstrapRequest:
    ticker: str
    asset_type: str


@dataclass(frozen=True)
class AssetBootstrapCapabilityResult:
    capability: AssetBootstrapCapabilityName
    ok: bool
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["capability"] = self.capability.value
        return payload


@dataclass(frozen=True)
class AssetBootstrapReport:
    ticker: str
    asset_type: str
    ok: bool
    capabilities: tuple[AssetBootstrapCapabilityResult, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "ticker": self.ticker,
            "asset_type": self.asset_type,
            "ok": self.ok,
            "capabilities": [item.to_dict() for item in self.capabilities],
        }


class AssetBootstrapCapability(Protocol):
    name: AssetBootstrapCapabilityName

    async def execute(
        self,
        request: AssetBootstrapRequest,
    ) -> AssetBootstrapCapabilityResult:
        """Executa uma capacidade isolada sem assumir provider ou transação."""
