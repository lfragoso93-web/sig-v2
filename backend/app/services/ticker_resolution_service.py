"""Orquestracao de resolucao de tickers e persistencia de aliases historicos."""

from dataclasses import dataclass
from datetime import date
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.brapi_v2_client import BrapiV2Client, BrapiV2Error, TickerResolution
from app.models.asset import Asset
from app.models.asset_alias import AssetAlias


@dataclass(frozen=True)
class ResolvedTicker:
    requested_ticker: str
    current_ticker: str
    changed: bool
    status: str
    effective_date: Optional[date] = None


class TickerResolutionService:
    def __init__(self, client: Optional[BrapiV2Client] = None) -> None:
        self._client = client or BrapiV2Client()

    async def resolve_many(self, tickers: Sequence[str]) -> dict[str, ResolvedTicker]:
        normalized = self._normalize(tickers)
        if not normalized:
            return {}

        try:
            provider_results = await self._client.resolve_tickers(normalized)
        except BrapiV2Error:
            return {
                ticker: ResolvedTicker(
                    requested_ticker=ticker,
                    current_ticker=ticker,
                    changed=False,
                    status="unavailable",
                )
                for ticker in normalized
            }

        by_requested = {item.requested_symbol: item for item in provider_results}
        return {
            ticker: self._to_resolved(ticker, by_requested.get(ticker))
            for ticker in normalized
        }

    async def persist_alias(
        self,
        db: AsyncSession,
        *,
        asset: Asset,
        resolution: ResolvedTicker,
        source_provider: str = "market_data_provider",
    ) -> Optional[AssetAlias]:
        if not resolution.changed or resolution.requested_ticker == resolution.current_ticker:
            return None

        existing = await db.execute(
            select(AssetAlias).where(
                AssetAlias.alias_ticker == resolution.requested_ticker,
                AssetAlias.asset_type == str(asset.asset_type),
            )
        )
        alias = existing.scalar_one_or_none()
        if alias is not None:
            return alias

        alias = AssetAlias(
            asset_id=asset.id,
            alias_ticker=resolution.requested_ticker,
            asset_type=str(asset.asset_type),
            effective_from=resolution.effective_date,
            source_provider=source_provider,
        )
        db.add(alias)
        await db.flush()
        return alias

    @staticmethod
    def _normalize(tickers: Sequence[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for ticker in tickers:
            value = ticker.strip().upper()
            if value and value not in seen:
                seen.add(value)
                result.append(value)
        return result

    @staticmethod
    def _to_resolved(
        requested_ticker: str,
        provider_result: Optional[TickerResolution],
    ) -> ResolvedTicker:
        if provider_result is None:
            return ResolvedTicker(
                requested_ticker=requested_ticker,
                current_ticker=requested_ticker,
                changed=False,
                status="not_found",
            )

        return ResolvedTicker(
            requested_ticker=provider_result.requested_symbol,
            current_ticker=provider_result.symbol,
            changed=provider_result.changed,
            status=provider_result.status,
            effective_date=provider_result.effective_date,
        )
