"""Complemento histórico para o seed de proventos.

A BRAPI permanece como fonte principal dos eventos corporativos. Este serviço usa
Yahoo Finance apenas para preencher datas anteriores ao evento mais antigo já
armazenado para o ativo, evitando sobrepor eventos ricos (Data Com, JCP etc.).
"""
from __future__ import annotations

import asyncio
import logging
import warnings
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.dividend import DividendType
from app.services.dividend_backfill_service import materialize_asset_dividends

logger = logging.getLogger(__name__)

SKIP_TYPES = {"CRIPTO", "TESOURO_DIRETO", "RENDA_FIXA"}
NATIONAL_TYPES = {"ACAO", "FII", "ETF_NACIONAL", "BDR"}


def _yf_symbol(ticker: str, asset_type: str) -> str:
    ticker = ticker.upper().strip()
    if asset_type.upper() in NATIONAL_TYPES and not ticker.endswith(".SA"):
        return f"{ticker}.SA"
    return ticker


def _event_type(asset_type: str) -> DividendType:
    return DividendType.RENDIMENTO if asset_type.upper() == "FII" else DividendType.DIVIDENDO


async def _fetch_full_history(ticker: str, asset_type: str) -> list[tuple[date, float]]:
    """Busca dividendos sem depender de ``period=max``.

    Alguns tickers recém-listados expõem somente períodos curtos no Yahoo. Usar
    ``start``/``end`` evita que essa limitação gere exceção e mantém o retorno
    vazio como um caso normal para ativos sem histórico disponível.
    """
    symbol = _yf_symbol(ticker, asset_type)

    def _sync() -> list[tuple[date, float]]:
        import yfinance as yf

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            history = yf.Ticker(symbol).history(
                start="1970-01-01",
                end=(date.today() + timedelta(days=1)).isoformat(),
                actions=True,
                auto_adjust=False,
            )

        if history.empty or "Dividends" not in history.columns:
            return []

        rows: list[tuple[date, float]] = []
        for timestamp, value in history["Dividends"].items():
            amount = float(value or 0)
            if amount <= 0:
                continue
            event_date = (
                timestamp.date()
                if hasattr(timestamp, "date")
                else date.fromisoformat(str(timestamp)[:10])
            )
            rows.append((event_date, amount))
        return rows

    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="dividend_history") as pool:
        return await loop.run_in_executor(pool, _sync)


async def seed_full_dividend_history(
    db: AsyncSession,
    ticker: str,
    asset_type: str,
) -> int:
    """Persiste o histórico anterior à cobertura principal e materializa carteiras.

    A escrita é idempotente pela constraint
    ``uq_asset_dividend_asset_exdate_type``. Assim, reexecutar o seed nunca deve
    abortar o processamento do ativo por eventos já existentes.
    """
    ticker = ticker.upper().strip()
    asset_type = asset_type.upper().strip()
    if not ticker or asset_type in SKIP_TYPES:
        return 0

    asset_result = await db.execute(
        select(Asset).where(Asset.ticker == ticker, Asset.asset_type == asset_type)
    )
    asset = asset_result.scalar_one_or_none()
    if asset is None:
        return 0

    earliest_result = await db.execute(
        select(func.min(AssetDividend.ex_date)).where(AssetDividend.asset_id == asset.id)
    )
    earliest_existing = earliest_result.scalar_one_or_none()

    try:
        history = await _fetch_full_history(ticker, asset_type)
    except Exception as exc:
        logger.warning("[dividend_history] histórico indisponível para %s: %s", ticker, exc)
        return 0

    if not history:
        logger.debug("[dividend_history] %s sem histórico complementar disponível", ticker)
        return 0

    dividend_type = _event_type(asset_type)
    inserted = 0

    for event_date, amount in history:
        # A BRAPI continua responsável pela cobertura principal e pelos campos
        # ricos. O Yahoo complementa somente datas anteriores ao primeiro evento
        # conhecido dessa fonte principal.
        if earliest_existing is not None and event_date >= earliest_existing:
            continue

        stmt = (
            pg_insert(AssetDividend)
            .values(
                asset_id=asset.id,
                record_date=None,
                ex_date=event_date,
                payment_date=event_date,
                value_per_unit=Decimal(str(amount)),
                dividend_type=dividend_type,
                source="yfinance_history",
                raw_payload={
                    "source": "yfinance",
                    "symbol": _yf_symbol(ticker, asset_type),
                    "historical_seed": True,
                },
            )
            .on_conflict_do_nothing(constraint="uq_asset_dividend_asset_exdate_type")
        )
        result = await db.execute(stmt)
        if result.rowcount and result.rowcount > 0:
            inserted += 1

    if inserted:
        await db.flush()
        materialized = await materialize_asset_dividends(
            db=db,
            tickers=[ticker],
            commit=False,
        )
        await db.commit()
        logger.info(
            "[dividend_history] %s: %s eventos históricos inseridos, %s direitos materializados",
            ticker,
            inserted,
            materialized,
        )
    else:
        # Libera qualquer transação de leitura aberta pela sessão sem gerar
        # alteração no banco.
        await db.rollback()
        logger.debug("[dividend_history] %s já estava atualizado", ticker)

    return inserted
