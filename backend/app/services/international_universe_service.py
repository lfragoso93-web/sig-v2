"""Serviço de universo e catálogo canônico de ativos internacionais (Stocks e ETFs globais)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType

# Universo base de referência de Stocks internacionais mais negociadas
BASE_INTERNATIONAL_STOCKS: list[tuple[str, str]] = [
    ("AAPL", "Apple Inc."),
    ("MSFT", "Microsoft Corporation"),
    ("NVDA", "NVIDIA Corporation"),
    ("AMZN", "Amazon.com Inc."),
    ("GOOGL", "Alphabet Inc. (Class A)"),
    ("META", "Meta Platforms Inc."),
    ("TSLA", "Tesla Inc."),
    ("BRK.B", "Berkshire Hathaway Inc. (Class B)"),
    ("JNJ", "Johnson & Johnson"),
    ("V", "Visa Inc."),
    ("JPM", "JPMorgan Chase & Co."),
    ("PG", "Procter & Gamble Co."),
    ("MA", "Mastercard Inc."),
    ("HD", "Home Depot Inc."),
    ("DIS", "Walt Disney Co."),
    ("NFLX", "Netflix Inc."),
    ("ADBE", "Adobe Inc."),
    ("CRM", "Salesforce Inc."),
    ("AMD", "Advanced Micro Devices Inc."),
    ("QCOM", "Qualcomm Inc."),
    ("COST", "Costco Wholesale Corporation"),
    ("PEP", "PepsiCo Inc."),
    ("KO", "Coca-Cola Company"),
    ("WMT", "Walmart Inc."),
    ("INTC", "Intel Corporation"),
    ("AVGO", "Broadcom Inc."),
    ("CSCO", "Cisco Systems Inc."),
    ("TXN", "Texas Instruments Inc."),
    ("UNH", "UnitedHealth Group Inc."),
    ("XOM", "Exxon Mobil Corporation"),
]

# Universo base de referência de ETFs internacionais líderes globais
BASE_INTERNATIONAL_ETFS: list[tuple[str, str]] = [
    ("VOO", "Vanguard S&P 500 ETF"),
    ("SPY", "SPDR S&P 500 ETF Trust"),
    ("IVV", "iShares Core S&P 500 ETF"),
    ("QQQ", "Invesco QQQ Trust (Nasdaq-100)"),
    ("VTI", "Vanguard Total Stock Market ETF"),
    ("VEA", "Vanguard FTSE Developed Markets ETF"),
    ("VWO", "Vanguard FTSE Emerging Markets ETF"),
    ("VNQ", "Vanguard Real Estate ETF"),
    ("BND", "Vanguard Total Bond Market ETF"),
    ("VT", "Vanguard Total World Stock ETF"),
    ("SCHD", "Schwab U.S. Dividend Equity ETF"),
    ("DIA", "SPDR Dow Jones Industrial Average ETF"),
]


@dataclass(frozen=True)
class SupportedInternationalAsset:
    ticker: str
    name: str
    asset_type: str
    currency: str = "USD"


async def fetch_supported_international_universe(
    db: AsyncSession,
) -> list[SupportedInternationalAsset]:
    """Retorna lista consolidada e deduplicada de ativos internacionais suportados."""
    universe: dict[str, SupportedInternationalAsset] = {}

    # 1. Popula com o universo base curado de Stocks
    for ticker, name in BASE_INTERNATIONAL_STOCKS:
        clean_ticker = ticker.strip().upper()
        universe[clean_ticker] = SupportedInternationalAsset(
            ticker=clean_ticker,
            name=name,
            asset_type=AssetType.STOCK.value,
            currency="USD",
        )

    # 2. Popula com o universo base curado de ETFs
    for ticker, name in BASE_INTERNATIONAL_ETFS:
        clean_ticker = ticker.strip().upper()
        universe[clean_ticker] = SupportedInternationalAsset(
            ticker=clean_ticker,
            name=name,
            asset_type=AssetType.ETF_INTERNACIONAL.value,
            currency="USD",
        )

    # 3. Inclui ativos internacionais já existentes no banco de dados (ex: cadastrados por transações)
    db_assets_query = select(Asset.ticker, Asset.name, Asset.asset_type, Asset.currency).where(
        (Asset.asset_type.in_((AssetType.STOCK.value, AssetType.ETF_INTERNACIONAL.value)))
        | (Asset.currency == "USD")
    )
    db_assets = (await db.execute(db_assets_query)).all()
    for row in db_assets:
        clean_ticker = str(row[0]).strip().upper()
        if clean_ticker and clean_ticker not in universe:
            universe[clean_ticker] = SupportedInternationalAsset(
                ticker=clean_ticker,
                name=str(row[1]) if row[1] else clean_ticker,
                asset_type=str(row[2]) if row[2] else AssetType.STOCK.value,
                currency="USD",
            )

    return sorted(universe.values(), key=lambda a: a.ticker)
