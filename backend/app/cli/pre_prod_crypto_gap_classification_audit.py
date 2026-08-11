"""Classifica, sem writes/providers, gaps de costura CRIPTO persistidos."""
from __future__ import annotations

import asyncio
import json

from app.cli import pre_prod_crypto_seam_audit

TARGET_STATUS = "HISTORY_START_COMPLEMENT_GAPPED"


def _gap_bucket(gap_days: int | None) -> str:
    if gap_days is None:
        return "unknown"
    if gap_days <= 30:
        return "up_to_30_days"
    if gap_days <= 90:
        return "31_to_90_days"
    if gap_days <= 365:
        return "91_to_365_days"
    return "over_365_days"


async def _run() -> dict:
    seam = await pre_prod_crypto_seam_audit._run()
    assets: list[dict] = []
    by_gap_bucket = {
        "up_to_30_days": 0,
        "31_to_90_days": 0,
        "91_to_365_days": 0,
        "over_365_days": 0,
        "unknown": 0,
    }

    for item in seam["assets"]:
        if item["provider_status"] != TARGET_STATUS:
            continue

        gap_days = item["gap_days"]
        bucket = _gap_bucket(gap_days)
        by_gap_bucket[bucket] += 1
        sources = item["sources"]
        complement = sources.get(pre_prod_crypto_seam_audit.COMPLEMENT_SOURCE)
        brapi = sources.get(pre_prod_crypto_seam_audit.BRAPI_SOURCE)

        assets.append(
            {
                "asset_id": item["asset_id"],
                "ticker": item["ticker"],
                "provider": item.get("provider"),
                "provider_symbol": item.get("provider_symbol"),
                "provider_status": item["provider_status"],
                "provider_attempts": item.get("provider_attempts"),
                "first_history_date": min(
                    (
                        source["first_date"]
                        for source in sources.values()
                        if source["first_date"] is not None
                    ),
                    default=None,
                ),
                "last_complement_date": complement["last_date"] if complement else None,
                "first_brapi_date": brapi["first_date"] if brapi else None,
                "last_history_date": max(
                    (
                        source["last_date"]
                        for source in sources.values()
                        if source["last_date"] is not None
                    ),
                    default=None,
                ),
                "gap_days": gap_days,
                "gap_bucket": bucket,
                "source_before_gap": pre_prod_crypto_seam_audit.COMPLEMENT_SOURCE
                if complement
                else None,
                "source_after_gap": pre_prod_crypto_seam_audit.BRAPI_SOURCE if brapi else None,
                "cause_classification": "requires_external_evidence",
            }
        )

    return {
        "read_only": True,
        "provider_calls": False,
        "target_status": TARGET_STATUS,
        "classified": len(assets),
        "by_gap_bucket": by_gap_bucket,
        "assets": assets,
    }


def main() -> None:
    print(json.dumps(asyncio.run(_run()), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
