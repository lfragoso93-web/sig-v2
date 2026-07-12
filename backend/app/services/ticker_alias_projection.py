"""Regras de projeção de tickers antigos para o ativo atual."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_alias import AssetAlias


@dataclass(frozen=True)
class TickerAliasRule:
    alias_ticker: str
    asset_type: str
    current_ticker: str
    effective_from: date


async def load_ticker_alias_rules(db: AsyncSession) -> dict[tuple[str, str], TickerAliasRule]:
    result = await db.execute(
        select(AssetAlias, Asset)
        .join(Asset, Asset.id == AssetAlias.asset_id)
        .where(AssetAlias.effective_from.is_not(None))
    )

    rules: dict[tuple[str, str], TickerAliasRule] = {}
    for alias, asset in result.all():
        effective_from = alias.effective_from
        if effective_from is None:
            continue
        key = (str(alias.alias_ticker).upper(), str(alias.asset_type).upper())
        rules[key] = TickerAliasRule(
            alias_ticker=key[0],
            asset_type=key[1],
            current_ticker=str(asset.ticker).upper(),
            effective_from=effective_from,
        )
    return rules


def project_transaction_ticker(
    ticker: str,
    asset_type: str,
    transaction_date: date,
    rules: dict[tuple[str, str], TickerAliasRule],
) -> str:
    normalized_ticker = ticker.strip().upper()
    normalized_type = asset_type.strip().upper()
    rule = rules.get((normalized_ticker, normalized_type))
    if rule is None:
        return normalized_ticker

    if transaction_date < rule.effective_from:
        return rule.current_ticker

    return normalized_ticker
