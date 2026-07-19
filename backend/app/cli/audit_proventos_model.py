"""Imprime o inventário pré-migração do modelo de proventos em JSON."""

import asyncio
import json

from app.core.database import AsyncSessionLocal
from app.services.proventos_model_audit_service import audit_proventos_model


async def main() -> None:
    async with AsyncSessionLocal() as db:
        report = await audit_proventos_model(db)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
