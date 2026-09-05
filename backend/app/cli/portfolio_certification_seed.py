"""Thin CLI for local portfolio certification seed issue #303."""

from __future__ import annotations

import asyncio
import os

from app.certification.portfolio_seed_identity_service import (
    provision_synthetic_user_portfolio,
)
from app.certification.portfolio_seed_transaction_service import (
    seed_non_crypto_transactions,
)
from app.core.database import AsyncSessionLocal


PASSWORD_ENV = "SGI_CERT303_PASSWORD"


async def _run() -> None:
    password = os.getenv(PASSWORD_ENV)
    if not password:
        raise SystemExit(f"{PASSWORD_ENV} is required")

    async with AsyncSessionLocal() as db:
        identity = await provision_synthetic_user_portfolio(db, password=password)
        transactions = await seed_non_crypto_transactions(
            db,
            portfolio_id=identity.portfolio_id,
        )

    print(
        "CERT303-SEED "
        f"user_id={identity.user_id} "
        f"portfolio_id={identity.portfolio_id} "
        f"user_created={str(identity.user_created).lower()} "
        f"portfolio_created={str(identity.portfolio_created).lower()} "
        f"transactions_created={transactions.created} "
        f"transactions_reused={transactions.reused} "
        f"blocked_crypto={transactions.blocked_crypto}"
    )


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
