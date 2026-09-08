"""Reconcilia gaps CRIPTO persistidos para status terminal sem providers."""
from __future__ import annotations

import argparse
import asyncio
import json
from typing import cast

from sqlalchemy import CursorResult, func, select, update

from app.cli import pre_prod_crypto_seam_audit
from app.core.database import AsyncSessionLocal
from app.models.asset import Asset, AssetType
from app.models.asset_universe_membership import AssetUniverseMembership
from app.services.asset_universe_membership_service import CRYPTO_TOP100_UNIVERSE_KEY

TARGET_STATUS = "HISTORY_START_COMPLEMENT_GAPPED"
SOURCE_STATUS = "ACTIVE"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Marca CRIPTO com gap BRAPI/Yahoo comprovado em banco como "
            "HISTORY_START_COMPLEMENT_GAPPED."
        )
    )
    parser.add_argument("--ticker", action="append", default=None)
    parser.add_argument("--all-crypto", action="store_true")
    parser.add_argument("--apply", action="store_true")
    return parser


def _normalize_tickers(values: list[str] | None) -> set[str] | None:
    if values is None:
        return None
    tickers = {str(value).strip().upper() for value in values if str(value).strip()}
    return tickers or None


async def _top100_tickers() -> set[str]:
    stmt = (
        select(func.upper(Asset.ticker))
        .join(AssetUniverseMembership, AssetUniverseMembership.asset_id == Asset.id)
        .where(Asset.asset_type == AssetType.CRIPTO.value)
        .where(AssetUniverseMembership.universe_key == CRYPTO_TOP100_UNIVERSE_KEY)
    )
    async with AsyncSessionLocal() as db:
        return {str(ticker).upper() for ticker in (await db.execute(stmt)).scalars().all()}


async def _run(*, tickers: set[str] | None, all_crypto: bool, apply: bool) -> dict:
    scoped_tickers = tickers
    scope = "requested_tickers"
    if scoped_tickers is None and not all_crypto:
        scoped_tickers = await _top100_tickers()
        scope = CRYPTO_TOP100_UNIVERSE_KEY
    elif all_crypto:
        scope = "all_crypto"

    seam = await pre_prod_crypto_seam_audit._run(tickers=scoped_tickers)
    candidates = [
        item
        for item in seam["assets"]
        if item["seam_status"] == "gapped"
        and str(item.get("provider_status") or "").upper() == SOURCE_STATUS
    ]

    updated = 0
    if apply and candidates:
        candidate_ids = [int(item["asset_id"]) for item in candidates]
        async with AsyncSessionLocal() as db:
            statement = (
                update(Asset)
                .where(Asset.asset_type == AssetType.CRIPTO.value)
                .where(Asset.id.in_(candidate_ids))
                .where(Asset.provider_status == SOURCE_STATUS)
                .values(provider_status=TARGET_STATUS)
            )
            result = cast(CursorResult, await db.execute(statement))
            updated = int(result.rowcount or 0)
            await db.commit()

    return {
        "apply": apply,
        "scope": scope,
        "target_status": TARGET_STATUS,
        "audited": int(seam["audited"]),
        "gapped": int(seam["by_seam_status"]["gapped"]),
        "selected": len(candidates),
        "updated": updated,
        "assets": [
            {
                "asset_id": item["asset_id"],
                "ticker": item["ticker"],
                "provider_status_before": item.get("provider_status"),
                "provider_status_after": TARGET_STATUS if apply else item.get("provider_status"),
                "gap_days": item.get("gap_days"),
                "expected_complement_end": item.get("expected_complement_end"),
            }
            for item in candidates
        ],
    }


def main() -> None:
    args = _parser().parse_args()
    result = asyncio.run(
        _run(
            tickers=_normalize_tickers(args.ticker),
            all_crypto=bool(args.all_crypto),
            apply=bool(args.apply),
        )
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
