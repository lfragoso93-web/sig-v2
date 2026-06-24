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
  Tickers sem historico na BRAPI sao filtrados ANTES do backfill para evitar
  requests desnecessarios. Os sufixos filtrados sao:
    *F  -> direitos de subscricao fracionarios (ABCB4F, AALR3F, ...)
    *R  -> recibos de subscricao (PETR4R, ...)
    *B  -> bonus de subscricao
    *D  -> debentures / codigos especiais
  O roteamento e feito por asset_type:
    FII -> /api/v2/fii/historical
    demais -> /api/v2/stocks/historical
  O backfill e executado em lotes de BACKFILL_CONCURRENCY para nao sobrecarregar
  a BRAPI e o banco simultaneamente.
"""
import asyncio
import logging
import re
from dataclasses import dataclass, field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.integrations.brapi import fetch_all_tickers_v2

logger = logging.getLogger(__name__)

# Subtipos BRAPI e o AssetType interno correspondente.
_SEED_TYPES: list[tuple[str, AssetType]] = [
    ("stock",    AssetType.ACAO),
    ("unit",     AssetType.ACAO),
    ("fii",      AssetType.FII),
    ("fi-infra", AssetType.FII),
    ("fi-agro",  AssetType.FII),
    ("etf",      AssetType.ETF_NACIONAL),
    ("bdr",      AssetType.BDR),
]

# Sufixos B3 que nao possuem historico de precos na BRAPI.
# Tickers com esses sufixos sao cadastrados como ativos,
# mas excluidos do backfill de historico.
# Regex: ticker termina com letra(s) nao numerica(s) apos os digitos.
# Exemplos filtrados: ABCB4F, PETR4R, VALE3B, BOVA11D
_NO_HISTORY_SUFFIX_RE = re.compile(r"^[A-Z]{4}\d+[FRBD]$")

# Quantos ativos processar em paralelo no backfill de historico.
# Valor conservador para nao saturar BRAPI e yfinance.
BACKFILL_CONCURRENCY = 2

# Quantos dias de historico buscar no backfill inicial.
BACKFILL_DAYS = 365 * 5  # 5 anos


@dataclass
class SeedResult:
    created:  int = 0
    updated:  int = 0
    skipped:  int = 0
    errors:   int = 0
    by_type:  dict[str, int] = field(default_factory=dict)
    # Tickers criados nesta execucao elegiveis para backfill.
    new_tickers: dict[str, list[str]] = field(default_factory=dict)
    # Tickers criados mas filtrados do backfill (sem historico).
    skipped_backfill: int = 0


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


def _has_history(ticker: str) -> bool:
    """
    Retorna False para tickers B3 que nao possuem historico de precos
    na BRAPI (direitos de subscricao, recibos, bonus, debentures).
    """
    return not _NO_HISTORY_SUFFIX_RE.match(ticker)


async def _backfill_history_for_ticker(
    ticker: str,
    asset_type: AssetType,
) -> None:
    """
    Dispara o backfill de historico para um ativo, usando sua propria sessao DB.
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
    Executa o backfill de historico para ativos criados no seed.
    Filtra tickers sem historico antes de processar.
    Processa em lotes de BACKFILL_CONCURRENCY.
    """
    tasks: list[tuple[str, AssetType]] = []
    filtered = 0

    for type_value, tickers in new_tickers.items():
        try:
            at = AssetType(type_value)
        except ValueError:
            continue
        for t in tickers:
            if _has_history(t):
                tasks.append((t, at))
            else:
                filtered += 1

    if filtered:
        logger.info(f"[seed_backfill] {filtered} tickers sem historico ignorados (sufixos F/R/B/D)")

    if not tasks:
        logger.info("[seed_backfill] nenhum ativo elegivel para backfill")
        return

    logger.info(f"[seed_backfill] iniciando backfill de {len(tasks)} ativos")
    total_done = 0

    for i in range(0, len(tasks), BACKFILL_CONCURRENCY):
        batch = tasks[i:i + BACKFILL_CONCURRENCY]
        await asyncio.gather(
            *[_backfill_history_for_ticker(ticker, at) for ticker, at in batch],
            return_exceptions=True,
        )
        total_done += len(batch)
        if total_done % 20 == 0:
            logger.info(f"[seed_backfill] {total_done}/{len(tasks)} ativos processados")

    logger.info(f"[seed_backfill] backfill concluido: {total_done} ativos, {filtered} ignorados")


async def run_asset_seed(db: AsyncSession, run_backfill: bool = True) -> SeedResult:
    """
    Ponto de entrada do seed. Recebe uma sessao de banco ja aberta.
    Faz commit em lotes de 200 para nao sobrecarregar a transacao.

    Se run_backfill=True (padrao), ao final do seed dispara o backfill
    de historico de precos para todos os ativos criados nesta execucao
    que possuam historico disponivel na BRAPI.
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
                    # Registra para backfill independente de ter historico;
                    # a filtragem e feita em _run_backfill.
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

    if run_backfill and result.created > 0:
        logger.info(f"[seed] iniciando backfill para {result.created} ativos novos")
        await _run_backfill(result.new_tickers)
    else:
        logger.info("[seed] sem ativos novos — backfill ignorado")

    return result
