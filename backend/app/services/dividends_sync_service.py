"""
DividendsSyncService — bootstrap e sync incremental de proventos FIIs.

Responsabilidades:
  1. Acquire/release de lock em dividends_sync_jobs (expiracy 60 min).
  2. Busca todos os FIIs distintos com posicao > 0 via asset_type='FII'.
  3. Chama get_fii_dividends_chunked() (lote de ate 20 simbolos).
  4. Upsert idempotente em asset_dividends usando constraint
     uq_asset_dividend_asset_exdate_type.
  5. Atualiza cursor (last_cursor_date) e registra metricas/erros.

Modo bootstrap  : sem cursor, busca a partir de BOOTSTRAP_YEARS_BACK anos.
Modo incremental: cursor presente, busca a partir de (cursor - LOOKBACK_DAYS).

Nao interfere com dividend_backfill_service.py — sao complementares:
  - backfill_service : per-ticker, triggered por transacao, usa /quote/{ticker}
  - dividends_sync  : batch FII, agendado, usa /fiis/dividendos
"""
import logging
import socket
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.brapi_fii_dividends_client import (
    FiiDividendEvent,
    get_fii_dividends_chunked,
)
from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.dividend import DividendType
from app.models.dividends_sync_job import DividendsSyncJob
from app.services.dividend_backfill_service import materialize_asset_dividends
from app.models.portfolio_position import PortfolioPosition

logger = logging.getLogger(__name__)

# ─── Constantes ──────────────────────────────────────────────────────────────
JOB_NAME_BOOTSTRAP = "fii_dividends_bootstrap"
JOB_NAME_INCREMENTAL = "fii_dividends_incremental"

BOOTSTRAP_YEARS_BACK = 5          # bootstrap busca N anos de historico
LOOKBACK_DAYS = 30                 # sync incremental volta N dias antes do cursor
LOCK_TIMEOUT_MINUTES = 60          # lock expira apos N min (previne lock eterno)
FII_ASSET_TYPE = "FII"             # valor de asset_type para FIIs na tabela assets


# ─── DTOs de resultado ────────────────────────────────────────────────────────
@dataclass
class SyncRunResult:
    job_name: str
    assets_processed: int = 0
    events_created: int = 0
    events_updated: int = 0
    errors: int = 0
    error_messages: list[str] = field(default_factory=list)
    cursor_date: Optional[date] = None
    success: bool = False


# ─── Helpers internos ─────────────────────────────────────────────────────────
def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _map_dividend_type(raw_type: str) -> DividendType:
    """
    Mapeia o tipo raw da BRAPI para DividendType do sistema.
    Tipos desconhecidos caem em RENDIMENTO (padrao FII).
    """
    mapping = {
        "DIVIDENDO": DividendType.DIVIDENDO,
        "JCP": DividendType.JCP,
        "RENDIMENTO": DividendType.RENDIMENTO,
        "AMORTIZACAO": DividendType.AMORTIZACAO,
        "AMORTIZAÇÃO": DividendType.AMORTIZACAO,
        "BONIFICACAO": DividendType.BONIFICACAO,
        "BONIFICAÇÃO": DividendType.BONIFICACAO,
    }
    return mapping.get(raw_type.upper().strip(), DividendType.RENDIMENTO)


async def _get_or_create_job(db: AsyncSession, job_name: str) -> DividendsSyncJob:
    """Busca ou cria o registro de controle do job."""
    result = await db.execute(
        select(DividendsSyncJob).where(DividendsSyncJob.job_name == job_name)
    )
    job = result.scalar_one_or_none()
    if job is None:
        job = DividendsSyncJob(job_name=job_name, status="idle")
        db.add(job)
        await db.flush()
    return job


async def _acquire_lock(db: AsyncSession, job: DividendsSyncJob) -> bool:
    """
    Tenta adquirir o lock no job.
    Retorna False se o lock estiver ativo e nao expirado.
    """
    if job.is_locked(lock_timeout_minutes=LOCK_TIMEOUT_MINUTES):
        logger.warning(
            f"[DividendsSync] Job '{job.job_name}' ja esta em execucao "
            f"(locked_by={job.locked_by}, locked_at={job.locked_at}). Abortando."
        )
        return False

    job.locked_by = socket.gethostname()
    job.locked_at = _now_utc()
    job.status = "running"
    job.started_at = _now_utc()
    job.error_message = None
    await db.flush()
    return True


async def _release_lock(
    db: AsyncSession,
    job: DividendsSyncJob,
    result: SyncRunResult,
) -> None:
    """Libera o lock e persiste metricas do run."""
    job.locked_by = None
    job.locked_at = None
    job.finished_at = _now_utc()
    job.last_run_assets_processed = result.assets_processed
    job.last_run_events_created = result.events_created
    job.last_run_events_updated = result.events_updated
    job.last_run_errors = result.errors

    if result.success:
        job.status = "success"
        job.last_success_at = _now_utc()
        if result.cursor_date:
            job.last_cursor_date = result.cursor_date
    else:
        job.status = "error"
        job.error_message = "\n".join(result.error_messages[-10:])  # ultimas 10 linhas

    await db.commit()


async def _fetch_fii_tickers(db: AsyncSession) -> list[tuple[int, str]]:
    """
    Retorna lista de (asset_id, ticker) de FIIs com posicao ativa no sistema.
    Usa DISTINCT para evitar duplicatas entre portfolios.
    """
    result = await db.execute(
        select(Asset.id, Asset.ticker)
        .join(PortfolioPosition, PortfolioPosition.asset_id == Asset.id)
        .where(
            Asset.asset_type == FII_ASSET_TYPE,
            PortfolioPosition.quantity > 0,
        )
        .distinct()
        .order_by(Asset.ticker)
    )
    return [(row.id, row.ticker) for row in result.all()]


async def _upsert_asset_dividends(
    db: AsyncSession,
    events: list[FiiDividendEvent],
    asset_id: int,
) -> tuple[int, int]:
    """
    Upsert dos eventos em asset_dividends.
    Retorna (created, updated).

    Estrategia:
      1. Pre-carrega AssetDividends existentes do asset_id em memoria.
      2. Loop sobre eventos sem queries adicionais.
    """
    # Pre-carrega existentes: chave = (ex_date, dividend_type)
    existing_result = await db.execute(
        select(AssetDividend).where(AssetDividend.asset_id == asset_id)
    )
    existing: dict[tuple[date, str], AssetDividend] = {
        (ad.ex_date, ad.dividend_type.value if hasattr(ad.dividend_type, 'value') else str(ad.dividend_type)): ad
        for ad in existing_result.scalars().all()
    }

    created = 0
    updated = 0

    for ev in events:
        if ev.ex_date is None:
            continue
        if ev.value_per_unit is None or float(ev.value_per_unit) <= 0:
            continue

        div_type = _map_dividend_type(ev.raw_type or ev.dividend_type or "RENDIMENTO")
        cache_key = (ev.ex_date, div_type.value)

        existing_ad = existing.get(cache_key)
        if existing_ad is None:
            new_ad = AssetDividend(
                asset_id=asset_id,
                ex_date=ev.ex_date,
                payment_date=ev.payment_date,
                dividend_type=div_type,
                value_per_unit=Decimal(str(ev.value_per_unit)),
                source="brapi_fii",
            )
            db.add(new_ad)
            existing[cache_key] = new_ad
            created += 1
        else:
            # Atualiza apenas se o valor mudou (correcao retroativa da BRAPI)
            new_value = Decimal(str(ev.value_per_unit))
            if existing_ad.value_per_unit != new_value:
                existing_ad.value_per_unit = new_value
                existing_ad.payment_date = ev.payment_date
                updated += 1

    return created, updated


# ─── Ponto de entrada publico ─────────────────────────────────────────────────
async def run_fii_dividends_sync(
    db: AsyncSession,
    force_bootstrap: bool = False,
) -> SyncRunResult:
    """
    Ponto de entrada principal. Chamado pelo APScheduler ou endpoint admin.

    Logica de modo:
      - Se nao houver cursor (last_cursor_date = None) ou force_bootstrap=True:
          bootstrap — busca BOOTSTRAP_YEARS_BACK anos de historico.
      - Caso contrario:
          incremental — busca a partir de (cursor - LOOKBACK_DAYS).

    Args:
        db: Sessao async SQLAlchemy.
        force_bootstrap: Forca modo bootstrap mesmo com cursor presente.

    Returns:
        SyncRunResult com metricas do run.
    """
    # Determina job_name pelo modo
    job_name = JOB_NAME_BOOTSTRAP if force_bootstrap else JOB_NAME_INCREMENTAL
    result = SyncRunResult(job_name=job_name)

    # 1. Acquire lock
    job = await _get_or_create_job(db, job_name)
    if not await _acquire_lock(db, job):
        return result  # ja em execucao, retorna sem erro

    try:
        # 2. Determina janela de datas
        is_bootstrap = force_bootstrap or job.last_cursor_date is None

        if is_bootstrap:
            start_date = date.today() - timedelta(days=BOOTSTRAP_YEARS_BACK * 365)
            logger.info(
                f"[DividendsSync] Modo BOOTSTRAP — start_date={start_date}"
            )
        else:
            start_date = job.last_cursor_date - timedelta(days=LOOKBACK_DAYS)
            logger.info(
                f"[DividendsSync] Modo INCREMENTAL — cursor={job.last_cursor_date} "
                f"start_date={start_date}"
            )

        end_date = date.today()

        # 3. Busca FIIs ativos
        fii_assets = await _fetch_fii_tickers(db)
        if not fii_assets:
            logger.info("[DividendsSync] Nenhum FII ativo encontrado. Encerrando.")
            result.success = True
            return result

        tickers = [ticker for _, ticker in fii_assets]
        asset_id_map = {ticker: asset_id for asset_id, ticker in fii_assets}
        result.assets_processed = len(tickers)

        logger.info(
            f"[DividendsSync] Processando {len(tickers)} FIIs: "
            f"{tickers[:10]}{'...' if len(tickers) > 10 else ''}"
        )

        # 4. Fetch em lote via brapi_fii_dividends_client
        events_by_ticker = await get_fii_dividends_chunked(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
        )

        # 5. Upsert por ticker
        max_event_date: Optional[date] = None

        for ticker, events in events_by_ticker.items():
            asset_id = asset_id_map.get(ticker)
            if asset_id is None:
                logger.warning(f"[DividendsSync] asset_id nao encontrado para {ticker}")
                result.errors += 1
                continue

            if not events:
                continue

            try:
                created, updated = await _upsert_asset_dividends(db, events, asset_id)
                result.events_created += created
                result.events_updated += updated

                # Atualiza cursor com a data mais recente dos eventos
                for ev in events:
                    if ev.ex_date and (max_event_date is None or ev.ex_date > max_event_date):
                        max_event_date = ev.ex_date

            except Exception as e:
                msg = f"Erro ao fazer upsert de {ticker}: {e}"
                logger.error(f"[DividendsSync] {msg}")
                result.errors += 1
                result.error_messages.append(msg)
                await db.rollback()
                continue

        materialized = await materialize_asset_dividends(
            db,
            tickers=tickers,
            commit=False,
        )

        # Flush acumulado (apos todos os tickers processados sem erro)
        await db.flush()

        result.cursor_date = max_event_date or end_date
        result.success = True

        logger.info(
            f"[DividendsSync] Concluido — "
            f"assets={result.assets_processed} "
            f"created={result.events_created} "
            f"updated={result.events_updated} "
            f"materialized={materialized} "
            f"errors={result.errors} "
            f"cursor={result.cursor_date}"
        )

    except Exception as e:
        msg = f"Erro fatal no job {job_name}: {e}"
        logger.exception(f"[DividendsSync] {msg}")
        result.errors += 1
        result.error_messages.append(msg)
        result.success = False
        try:
            await db.rollback()
        except Exception:
            pass

    finally:
        await _release_lock(db, job, result)

    return result
