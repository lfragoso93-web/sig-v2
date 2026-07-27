"""Inspeção read-only do estado persistido de séries macroeconômicas."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rate_history import RateHistory
from app.services.pre_prod_macro_seed_contract import (
    MACRO_SEED_INDICATORS,
    MacroIndicatorState,
    MacroSeedState,
)


async def inspect_macro_seed_state(db: AsyncSession) -> MacroSeedState:
    """Lê contagens, cobertura e duplicidades sem alterar a sessão."""

    total_rows = int(
        await db.scalar(select(func.count()).select_from(RateHistory)) or 0
    )

    unsupported_result = await db.execute(
        select(RateHistory.indicator)
        .where(RateHistory.indicator.not_in(MACRO_SEED_INDICATORS))
        .distinct()
        .order_by(RateHistory.indicator.asc())
    )
    unsupported_indicators = tuple(
        str(row.indicator) for row in unsupported_result.all()
    )

    indicators: list[MacroIndicatorState] = []
    for indicator in MACRO_SEED_INDICATORS:
        aggregate = await db.execute(
            select(
                func.count(RateHistory.id).label("rows"),
                func.min(RateHistory.date).label("first_date"),
                func.max(RateHistory.date).label("last_date"),
            ).where(RateHistory.indicator == indicator)
        )
        row = aggregate.one()

        duplicate_groups = await db.execute(
            select(
                RateHistory.indicator,
                RateHistory.date,
                func.count(RateHistory.id).label("rows"),
            )
            .where(RateHistory.indicator == indicator)
            .group_by(RateHistory.indicator, RateHistory.date)
            .having(func.count(RateHistory.id) > 1)
        )
        duplicate_rows = sum(
            max(int(item.rows) - 1, 0)
            for item in duplicate_groups.all()
        )

        indicators.append(
            MacroIndicatorState(
                indicator=indicator,
                rows=int(row.rows or 0),
                first_date=row.first_date.isoformat() if row.first_date else None,
                last_date=row.last_date.isoformat() if row.last_date else None,
                duplicate_rows=duplicate_rows,
            )
        )

    return MacroSeedState(
        total_rows=total_rows,
        indicators=tuple(indicators),
        unsupported_indicators=unsupported_indicators,
    )
