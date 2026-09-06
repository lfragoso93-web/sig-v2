"""Thin CLI for local portfolio certification seed issue #303."""

from __future__ import annotations

import asyncio
import os

from app.certification.portfolio_seed_dividend_service import seed_synthetic_dividends
from app.certification.portfolio_seed_identity_service import (
    provision_synthetic_user_portfolio,
)
from app.certification.portfolio_seed_market_price_service import (
    seed_generic_market_prices,
)
from app.certification.portfolio_seed_transaction_service import seed_transactions
from app.certification.portfolio_seed_treasury_price_service import (
    seed_synthetic_treasury_price,
)
from app.core.database import AsyncSessionLocal


PASSWORD_ENV = "SGI_CERT303_PASSWORD"


async def _run() -> None:
    password = os.getenv(PASSWORD_ENV)
    if not password:
        raise SystemExit(f"{PASSWORD_ENV} is required")

    async with AsyncSessionLocal() as db:
        identity = await provision_synthetic_user_portfolio(db, password=password)
        transactions = await seed_transactions(
            db,
            portfolio_id=identity.portfolio_id,
        )
        market_prices = await seed_generic_market_prices(db)
        dividends = await seed_synthetic_dividends(db)
        treasury_price = await seed_synthetic_treasury_price(db)

    print(
        "CERT303-SEED "
        f"user_id={identity.user_id} "
        f"portfolio_id={identity.portfolio_id} "
        f"user_created={str(identity.user_created).lower()} "
        f"portfolio_created={str(identity.portfolio_created).lower()} "
        f"transactions_created={transactions.created} "
        f"transactions_reused={transactions.reused} "
        f"crypto_membership_created={transactions.crypto_membership_created} "
        f"crypto_membership_reused={transactions.crypto_membership_reused} "
        f"market_prices_created={market_prices.created} "
        f"market_prices_reused={market_prices.reused} "
        f"dividends_created={dividends.created} "
        f"dividends_reused={dividends.reused} "
        f"treasury_prices_created={treasury_price.created} "
        f"treasury_prices_reused={treasury_price.reused}"
    )


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
