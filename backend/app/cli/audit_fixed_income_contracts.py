"""Executa a auditoria dos contratos de Renda Fixa cadastrados."""
from __future__ import annotations

import asyncio
import json

from app.core.database import AsyncSessionLocal
from app.services.fixed_income_contract_audit_service import audit_fixed_income_contracts


async def main() -> None:
    async with AsyncSessionLocal() as db:
        result = await audit_fixed_income_contracts(db)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
