"""
Asset Seed Service.

Popula (ou atualiza) a tabela `assets` com todos os ativos listados na B3
a partir do endpoint oficial BRAPI GET /api/v2/tickers.

Mapeamento de subtipos BRAPI -> AssetType interno:
  stock    -> ACAO   (acoes ordinarias e preferenciais)
  unit     -> ACAO   (units sao negociadas como acoes)
  fii      -> FII
  fi-infra -> FII    (fundos de infraestrutura, cotados como FII)
  fi-agro  -> FII    (fundos do agronegocio, cotados como FII)
  etf      -> ETF_NACIONAL
  bdr      -> BDR

Estrategia:
  - Para cada subtipo, busca todos os tickers via /api/v2/tickers com paginacao real.
  - Faz UPSERT por (ticker, asset_type): cria o registro se nao existir,
    atualiza name/sector se ja existir e esses campos estiverem vazios.
  - Nunca sobrescreve logo_url ou last_price ja preenchidos.
  - Retorna um SeedResult com contadores para log/debug.

Backfill de historico:
  Apos o seed, dispara persist_daily_prices para cada ativo criado nesta execucao.
  O roteamento e feito por asset_type:
    FII -> /api/v2/fii/historical
    demais -> /api/v2/stocks/historical
  O backfill e executado em lotes de BACKFILL_CONCURRENCY para nao sobrecarregar
  a BRAPI e o banco simultaneamente.
"""
import asyncio
import logging
from dataclasses import dataclass, field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.integrations.brapi import fetch_all_tickers_v2

logger = logging.getLogger(__name__)

# Subtipos BRAPI e o AssetType interno correspondente.
# unit e mapeado para ACAO pois e negociado da mesma forma.
# fi-infra e fi-agro sao mapeados para FII pois tem o mesmo comportamento de cota.
_SEED_TYPES: list[tuple[str, AssetType]] = [
    ("stock",    AssetType.ACAO),
    ("unit",     AssetType.ACAO),
    ("fii",      AssetType.FII),
    ("fi-infra", AssetType.FII),
    ("fi-agro",  AssetType.FII),
    ("etf",      AssetType.ETF_NACIONAL),
    ("bdr",      AssetType.BDR),
]

# Quantos ativos processar em paralelo no backfill de historico.
# Valor conservador para nao sobrecarregar BRAPI e DB.
BACKFILL_CONCURRENCY = 5

# Quantos dias de historico buscar no backfill inicial.
BACKFILL_DAYS = 365 * 5  # 5 anos


@dataclass
class SeedResult:
    created:  int = 0
    updated:  int = 0
    skipped:  int = 0
    errors:   int = 0
    by_type:  dict[str, int] = field(default_factory=dict)
    # Tickers criados nesta execucao, agrupados por asset_type,
    # para que o backfill saiba exatamente o que buscar.
    new_tickers: dict[str, list[str]] = field(default_factory=dict)


async def _upsert_asset(
    db: AsyncSession,
    ticker: str,
    name: str,
    asset_type: AssetType,
    sector: str | None,
) -> str:
    """
    Insere ou atualiza o ativo. Retorna 'created', 'updated' ou 'skipped'.
    Nunca sobrescreve logo_url ou last_price ja preenchidos.
    """
    result = await db.execute(
        select(Asset).where(
            Asset.ticker == ticker,
            Asset.asset_type == asset_type.value,
        )
    )
    existing = result.scalar_one_or_none()

    if existing is None:
        db.add(Asset(
            ticker=ticker,
            name=name or ticker,
            asset_type=asset_type.value,
            currency="BRL",
            sector=sector,
        ))
        return "created"

    changed = False
    if not existing.name and name:
        existing.name = name
        changed = True
    if not existing.sector and sector:
        existing.sector = sector
        changed = True

    return "updated" if changed else "skipped"


async def _backfill_history_for_ticker(
    ticker: str,
    asset_type: AssetType,
) -> None:
    """
    Dispara o backfill de historico para um ativo, usando sua propria sessao DB.
    Roteamento:
      FII -> fetch_fii_historical_v2 (endpoint /api/v2/fii/historical)
      demais -> fetch_stocks_historical_v2 (endpoint /api/v2/stocks/historical)
    """
    from app.core.database import AsyncSessionLocal
    from app.services.price_history_service import persist_daily_prices

    try:
        async with AsyncSessionLocal() as db:
            inserted = await persist_daily_prices(
                db=db,
                ticker=ticker,
                asset_type=asset_type,
                days_back=BACKFILL_DAYS,
            )
            logger.info(f"[seed_backfill] {ticker} ({asset_type.value}): {inserted} precos persistidos")
    except Exception as e:
        logger.error(f"[seed_backfill] erro em {ticker} ({asset_type.value}): {e}")


async def _run_backfill(new_tickers: dict[str, list[str]]) -> None:
    """
    Executa o backfill de historico para todos os ativos criados no seed.
    Processa em lotes de BACKFILL_CONCURRENCY para nao sobrecarregar a BRAPI.
    """
    # Monta lista plana de (ticker, asset_type)
    tasks: list[tuple[str, AssetType]] = []
    for type_value, tickers in new_tickers.items():
        try:
            at = AssetType(type_value)
        except ValueError:
            continue
        for t in tickers:
            tasks.append((t, at))

    if not tasks:
        logger.info("[seed_backfill] nenhum ativo novo para backfill")
        return

    logger.info(f"[seed_backfill] iniciando backfill de {len(tasks)} ativos novos")
    total_done = 0

    for i in range(0, len(tasks), BACKFILL_CONCURRENCY):
        batch = tasks[i:i + BACKFILL_CONCURRENCY]
        await asyncio.gather(
            *[_backfill_history_for_ticker(ticker, at) for ticker, at in batch],
            return_exceptions=True,
        )
        total_done += len(batch)
        logger.info(f"[seed_backfill] {total_done}/{len(tasks)} ativos processados")

    logger.info(f"[seed_backfill] backfill concluido para {total_done} ativos")


async def run_asset_seed(db: AsyncSession, run_backfill: bool = True) -> SeedResult:
    """
    Ponto de entrada do seed. Recebe uma sessao de banco ja aberta.
    Faz commit em lotes de 200 para nao sobrecarregar a transacao.

    Se run_backfill=True (padrao), ao final do seed dispara o backfill
    de historico de precos para todos os ativos criados nesta execucao.
    """
    result = SeedResult()
    BATCH_SIZE = 200
    batch_ops  = 0

    for brapi_subtype, asset_type in _SEED_TYPES:
        type_label = asset_type.value
        if type_label not in result.by_type:
            result.by_type[type_label]     = 0
            result.new_tickers[type_label] = []

        logger.info(f"[seed] iniciando subtype={brapi_subtype} -> {type_label}")
        items = await fetch_all_tickers_v2(brapi_subtype)
        logger.info(f"[seed] subtype={brapi_subtype}: {len(items)} ativos recebidos da BRAPI")

        for item in items:
            ticker = (
                item.get("stock")
                or item.get("symbol")
                or item.get("ticker")
                or ""
            ).strip().upper()
            if not ticker:
                result.errors += 1
                continue

            name   = (item.get("name") or item.get("longName") or "").strip()
            sector = (item.get("sector") or item.get("segment") or item.get("subSector") or "").strip() or None

            try:
                status = await _upsert_asset(db, ticker, name, asset_type, sector)
                if status == "created":
                    result.created += 1
                    result.by_type[type_label] += 1
                    result.new_tickers[type_label].append(ticker)
                elif status == "updated":
                    result.updated += 1
                else:
                    result.skipped += 1

                batch_ops += 1
                if batch_ops >= BATCH_SIZE:
                    await db.commit()
                    batch_ops = 0

            except Exception as e:
                result.errors += 1
                logger.error(f"[seed] erro ao upsert {ticker} ({type_label}): {e}")

    # Commit final do lote restante
    if batch_ops > 0:
        try:
            await db.commit()
        except Exception as e:
            logger.error(f"[seed] erro no commit final: {e}")

    logger.info(
        f"[seed] concluido: {result.created} criados, "
        f"{result.updated} atualizados, {result.skipped} sem mudanca, "
        f"{result.errors} erros | por tipo: {result.by_type}"
    )

    # Backfill de historico apenas para ativos recem-criados
    if run_backfill and result.created > 0:
        logger.info(f"[seed] iniciando backfill de historico para {result.created} ativos novos")
        await _run_backfill(result.new_tickers)
    else:
        logger.info("[seed] sem ativos novos — backfill de historico ignorado")

    return result
