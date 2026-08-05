"""Orquestrador neutro do bootstrap canônico de ativos."""

from __future__ import annotations

from collections.abc import Sequence

from app.services.asset_bootstrap_contracts import (
    AssetBootstrapCapability,
    AssetBootstrapReport,
    AssetBootstrapRequest,
)


class AssetBootstrapCoordinator:
    """Executa capacidades independentes em ordem explícita e auditável."""

    def __init__(self, capabilities: Sequence[AssetBootstrapCapability]) -> None:
        self._capabilities = tuple(capabilities)

    async def execute(self, request: AssetBootstrapRequest) -> AssetBootstrapReport:
        ticker = request.ticker.strip().upper()
        asset_type = request.asset_type.strip().upper()
        if not ticker:
            raise ValueError("ticker is required")
        if not asset_type:
            raise ValueError("asset_type is required")

        normalized_request = AssetBootstrapRequest(
            ticker=ticker,
            asset_type=asset_type,
        )
        results = []
        for capability in self._capabilities:
            result = await capability.execute(normalized_request)
            if result.capability is not capability.name:
                raise ValueError(
                    "capability result name does not match registered capability"
                )
            results.append(result)

        return AssetBootstrapReport(
            ticker=ticker,
            asset_type=asset_type,
            ok=all(result.ok for result in results),
            capabilities=tuple(results),
        )
