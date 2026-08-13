"""Emite o inventário read-only do legado de eventos corporativos em JSON."""

from __future__ import annotations

import asyncio
import json

from app.core.database import AsyncSessionLocal
from app.services.corporate_event_legacy_inventory_service import (
    load_corporate_event_legacy_inventory,
)

_SCHEMA_VERSION = "corporate-event-legacy-inventory.v1"


async def main() -> None:
    async with AsyncSessionLocal() as db:
        inventory = await load_corporate_event_legacy_inventory(db)

    payload = {
        "schema_version": _SCHEMA_VERSION,
        "read_only": True,
        "inventory": inventory.to_dict(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
