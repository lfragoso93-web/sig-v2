"""Inspeção read-only do estado persistido de câmbio."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fx_rate import FxRate
from app.services.pre_prod_fx_seed_contract import (
    FX_SEED_PAIRS,
    FxPairState,
    FxSeedState,
)


async def inspect_fx_seed_state(db: AsyncSession) -> FxSeedState:
    """Lê contagens, cobertura e duplicidades sem alterar a sessão."""

    total_rows = int(
        await db.scalar(select(func.count()).select_from(FxRate)) or 0
    )

    unsupported_result = await db.execute(
        select(FxRate.pair)
        .where(FxRate.pair.not_in(FX_SEED_PAIRS))
        .distinct()
        .order_by(FxRate.pair.asc())
    )
    unsupported_pairs = tuple(
        str(row.pair) for row in unsupported_result.all()
    )

    pairs: list[FxPairState] = []
    for pair in FX_SEED_PAIRS:
        aggregate = await db.execute(
            select(
                func.count(FxRate.id).label("rows"),
                func.min(FxRate.rate_date).label("first_date"),
                func.max(FxRate.rate_date).label("last_date"),
            ).where(FxRate.pair == pair)
        )
        row = aggregate.one()

        duplicate_groups = await db.execute(
            select(
                FxRate.pair,
                FxRate.rate_date,
                func.count(FxRate.id).label("rows"),
            )
            .where(FxRate.pair == pair)
            .group_by(FxRate.pair, FxRate.rate_date)
            .having(func.count(FxRate.id) > 1)
        )
        duplicate_rows = sum(
            max(int(item.rows) - 1, 0)
            for item in duplicate_groups.all()
        )

        pairs.append(
            FxPairState(
                pair=pair,
                rows=int(row.rows or 0),
                first_date=row.first_date.isoformat() if row.first_date else None,
                last_date=row.last_date.isoformat() if row.last_date else None,
                duplicate_rows=duplicate_rows,
            )
        )

    return FxSeedState(
        total_rows=total_rows,
        pairs=tuple(pairs),
        unsupported_pairs=unsupported_pairs,
    )
