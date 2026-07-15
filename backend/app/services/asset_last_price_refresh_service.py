"""Atualização DB-only do cache de último preço dos ativos.

Mantém a persistência do histórico desacoplada da tabela ``assets``. Isso reduz
contenção e evita deadlocks quando diferentes rotinas gravam ``asset_prices`` ao
mesmo tempo.
"""
from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def refresh_asset_last_prices(
    db: AsyncSession,
    asset_ids: Iterable[int] | None = None,
) -> int:
    """Atualiza ``last_price`` e ``last_price_updated_at`` em uma única query.

    Quando ``asset_ids`` é informado, somente esses ativos são atualizados. O
    retorno representa a quantidade de linhas afetadas.
    """
    normalized_ids = sorted({int(asset_id) for asset_id in (asset_ids or [])})
    where_clause = ""
    params: dict[str, object] = {}
    if normalized_ids:
        where_clause = "WHERE ap.asset_id = ANY(:asset_ids)"
        params["asset_ids"] = normalized_ids

    statement = text(
        f"""
        WITH latest_prices AS (
            SELECT DISTINCT ON (ap.asset_id)
                ap.asset_id,
                ap.close,
                ap.timestamp
            FROM asset_prices ap
            {where_clause}
            ORDER BY ap.asset_id, ap.timestamp DESC
        )
        UPDATE assets AS a
        SET
            last_price = lp.close,
            last_price_updated_at = lp.timestamp
        FROM latest_prices AS lp
        WHERE a.id = lp.asset_id
        """
    )
    result = await db.execute(statement, params)
    return int(result.rowcount or 0)
