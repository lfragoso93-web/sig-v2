"""CLI para auditar a estrutura dos recursos oficiais do Tesouro Transparente."""
from __future__ import annotations

import asyncio
import json

from app.services.treasury_transparente_audit_service import (
    audit_tesouro_transparente_resources,
)


async def _main() -> None:
    result = await audit_tesouro_transparente_resources()
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(_main())
