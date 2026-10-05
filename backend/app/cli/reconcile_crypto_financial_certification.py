"""Reconcilia certificacao financeira CRIPTO usando evidencias persistidas."""
from __future__ import annotations

import argparse
import asyncio
import json

from sqlalchemy import func, select, update

from app.cli import pre_prod_crypto_readiness_audit
from app.core.database import AsyncSessionLocal
from app.models.asset import Asset, AssetType
from app.models.asset_universe_membership import AssetUniverseMembership
from app.services.asset_universe_membership_service import CRYPTO_TOP100_UNIVERSE_KEY

CERTIFIED_STATUS = "HISTORY_START_EXHAUSTED"
SOURCE_STATUSES = {"ACTIVE", None, ""}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Promove CRIPTO para status financeiro certificado somente quando "
            "a auditoria DB-first comprova historico continuo, sem duplicatas e "
            "sem shallow history."
        )
    )
    parser.add_argument("--apply", action="store_true")
    return parser


async def _candidate_tickers() -> dict:
    audit = await pre_prod_crypto_readiness_audit._run()
    shallow = {
        str(item["ticker"]).upper()
        for item in audit["shallow_history_audit"]["assets"]
    }
    continuous = {
        str(item["ticker"]).upper()
        for item in audit["seam_audit"]["assets"]
        if item["seam_status"] == "continuous"
    }
    if audit["duplicates"] or audit["no_history"]:
        continuous = set()
    return {
        "audit": audit,
        "tickers": sorted(continuous - shallow),
    }


async def _run(*, apply: bool) -> dict:
    selected = await _candidate_tickers()
    tickers = selected["tickers"]
    updated = 0
    inspected: list[dict] = []
    eligible_ids: list[int] = []

    async with AsyncSessionLocal() as db:
        if tickers:
            rows = (
                await db.execute(
                    select(
                        Asset.id,
                        Asset.ticker,
                        Asset.provider_status,
                        func.count(AssetUniverseMembership.id).label("memberships"),
                    )
                    .join(
                        AssetUniverseMembership,
                        AssetUniverseMembership.asset_id == Asset.id,
                    )
                    .where(Asset.asset_type == AssetType.CRIPTO.value)
                    .where(func.upper(Asset.ticker).in_(tickers))
                    .where(
                        AssetUniverseMembership.universe_key
                        == CRYPTO_TOP100_UNIVERSE_KEY
                    )
                    .group_by(Asset.id, Asset.ticker, Asset.provider_status)
                    .order_by(Asset.ticker.asc())
                )
            ).all()
            inspected = [
                {
                    "asset_id": row.id,
                    "ticker": row.ticker,
                    "provider_status_before": row.provider_status,
                    "top100_memberships": int(row.memberships or 0),
                }
                for row in rows
            ]
            eligible_ids = [
                int(row.id)
                for row in rows
                if row.provider_status in SOURCE_STATUSES
            ]
            if apply and eligible_ids:
                result = await db.execute(
                    update(Asset)
                    .where(Asset.id.in_(eligible_ids))
                    .where(Asset.asset_type == AssetType.CRIPTO.value)
                    .where(
                        (Asset.provider_status == "ACTIVE")
                        | Asset.provider_status.is_(None)
                        | (Asset.provider_status == "")
                    )
                    .values(provider_status=CERTIFIED_STATUS)
                )
                updated = int(getattr(result, "rowcount", 0) or 0)
                await db.commit()

    return {
        "apply": apply,
        "certified_status": CERTIFIED_STATUS,
        "continuous_candidates": len(tickers),
        "membership_eligible": len(inspected),
        "updated": updated,
        "tickers": tickers,
        "skipped_without_membership": sorted(
            set(tickers) - {str(item["ticker"]).upper() for item in inspected}
        ),
        "already_terminal_or_blocked": len(inspected) - len(eligible_ids),
        "assets": inspected,
        "audit_summary": {
            "supported_universe_size": selected["audit"]["supported_universe_size"],
            "persisted_candidate_memberships": selected["audit"][
                "persisted_candidate_memberships"
            ],
            "blocking_seams": selected["audit"]["blocking_seams"],
            "shallow_histories": selected["audit"]["shallow_histories"],
            "duplicates": selected["audit"]["duplicates"],
            "no_history": selected["audit"]["no_history"],
        },
    }


def main() -> None:
    args = _parser().parse_args()
    print(json.dumps(asyncio.run(_run(apply=args.apply)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
