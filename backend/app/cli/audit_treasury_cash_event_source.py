"""Read-only audit of the official Treasury coupon-payment source."""
from __future__ import annotations

import asyncio
import json

from app.integrations.tesouro_transparente_cash_events import (
    audit_official_coupon_payments,
)


async def _main() -> None:
    report = await audit_official_coupon_payments()
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(_main())
