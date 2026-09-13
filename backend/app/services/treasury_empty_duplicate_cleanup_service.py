"""Cleanup protegido de duplicatas Tesouro vazias e conhecidas."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType

TARGET_EMPTY_DUPLICATE_IDS: tuple[int, ...] = (
    2870,
    2871,
    2872,
    2873,
    2874,
    2875,
    2876,
    2877,
    3720,
)

PRESERVED_SYNTHETIC_CERTIFICATION_ID = 2867
SYNTHETIC_CERTIFICATION_PROVIDER = "synthetic-certification"

_REFERENCE_SQL: tuple[tuple[str, str], ...] = (
    ("asset_prices", "select count(*) from asset_prices where asset_id = :asset_id"),
    (
        "transactions_exact",
        """
        select count(*)
        from transactions
        where asset_type = :asset_type and ticker = :ticker
        """,
    ),
    ("asset_aliases", "select count(*) from asset_aliases where asset_id = :asset_id"),
    ("asset_dividends", "select count(*) from asset_dividends where asset_id = :asset_id"),
    (
        "asset_universe_memberships",
        "select count(*) from asset_universe_memberships where asset_id = :asset_id",
    ),
    (
        "corporate_events_asset",
        "select count(*) from corporate_events where asset_id = :asset_id",
    ),
    (
        "corporate_events_destination",
        "select count(*) from corporate_events where destination_asset_id = :asset_id",
    ),
    (
        "portfolio_positions",
        "select count(*) from portfolio_positions where asset_id = :asset_id",
    ),
)


@dataclass(frozen=True)
class TreasuryEmptyDuplicateCleanupEntry:
    asset_id: int
    ticker: str
    reference_counts: dict[str, int]
    deletable: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "asset_id": self.asset_id,
            "ticker": self.ticker,
            "reference_counts": dict(self.reference_counts),
            "deletable": self.deletable,
        }


async def _reference_counts(db: AsyncSession, asset: Asset) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name, sql in _REFERENCE_SQL:
        result = await db.execute(
            text(sql),
            {
                "asset_id": int(asset.id),
                "asset_type": AssetType.TESOURO_DIRETO.value,
                "ticker": str(asset.ticker or ""),
            },
        )
        counts[name] = int(result.scalar_one())
    return counts


async def audit_empty_treasury_duplicate_cleanup(
    db: AsyncSession,
) -> dict[str, object]:
    result = await db.execute(
        select(Asset)
        .where(Asset.id.in_(TARGET_EMPTY_DUPLICATE_IDS))
        .order_by(Asset.id)
    )
    assets = list(result.scalars().all())

    entries: list[TreasuryEmptyDuplicateCleanupEntry] = []
    for asset in assets:
        counts = await _reference_counts(db, asset)
        deletable = (
            asset.asset_type == AssetType.TESOURO_DIRETO.value
            and int(asset.id) in TARGET_EMPTY_DUPLICATE_IDS
            and int(asset.id) != PRESERVED_SYNTHETIC_CERTIFICATION_ID
            and str(asset.provider or "").strip() != SYNTHETIC_CERTIFICATION_PROVIDER
            and all(count == 0 for count in counts.values())
        )
        entries.append(
            TreasuryEmptyDuplicateCleanupEntry(
                asset_id=int(asset.id),
                ticker=str(asset.ticker or ""),
                reference_counts=counts,
                deletable=deletable,
            )
        )

    blocked = [entry for entry in entries if not entry.deletable]
    return {
        "target_ids": TARGET_EMPTY_DUPLICATE_IDS,
        "preserved_ids": (PRESERVED_SYNTHETIC_CERTIFICATION_ID,),
        "found": len(entries),
        "deletable": [entry.to_dict() for entry in entries if entry.deletable],
        "blocked": [entry.to_dict() for entry in blocked],
        "ok": len(blocked) == 0,
    }


async def cleanup_empty_treasury_duplicate_assets(
    db: AsyncSession,
    *,
    dry_run: bool = True,
) -> dict[str, object]:
    audit = await audit_empty_treasury_duplicate_cleanup(db)
    if not audit["ok"]:
        return {**audit, "dry_run": dry_run, "deleted": 0}
    if dry_run:
        return {**audit, "dry_run": True, "deleted": 0}

    ids = [entry["asset_id"] for entry in audit["deletable"]]
    if not ids:
        return {**audit, "dry_run": False, "deleted": 0}

    result = await db.execute(
        delete(Asset).where(
            Asset.id.in_(ids),
            Asset.asset_type == AssetType.TESOURO_DIRETO.value,
            Asset.provider.is_(None),
        )
    )
    await db.commit()
    return {
        **audit,
        "dry_run": False,
        "deleted": int(result.rowcount or 0),
    }
