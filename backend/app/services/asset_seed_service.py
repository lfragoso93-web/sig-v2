"""
Asset Seed Service.

Popula (ou atualiza) a tabela `assets` com todos os ativos listados na B3
a partir do endpoint BRAPI GET /api/quote/list.

Estrategia:
  - Para cada tipo suportado (ACAO, FII, ETF_NACIONAL, BDR), chama a BRAPI
    com paginacao ate esgotar os resultados.
  - Faz UPSERT por (ticker, asset_type): cria o registro se nao existir,
    atualiza name/sector se ja existir e esses campos estiverem vazios.
  - Nunca sobrescreve logo_url ou last_price ja preenchidos.
  - Retorna um dict com contadores por tipo para facilitar o log/debug.
"""
import logging
from dataclasses import dataclass, field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.integrations.brapi import fetch_ticker_suggestions

logger = logging.getLogger(__name__)

# Mapeamento tipo BRAPI -> AssetType interno
_BRAPI_TYPE_MAP: dict[str, AssetType] = {
    "stock":       AssetType.ACAO,
    "acao":        AssetType.ACAO,
    "fii":         AssetType.FII,
    "funds":       AssetType.FII,
    "etf":         AssetType.ETF_NACIONAL,
    "etf_nacional": AssetType.ETF_NACIONAL,
    "bdr":         AssetType.BDR,
}

# Tipos que queremos semear e o termo de busca correspondente na BRAPI
_SEED_TYPES: list[tuple[str, AssetType]] = [
    ("stock",  AssetType.ACAO),
    ("fii",    AssetType.FII),
    ("etf",    AssetType.ETF_NACIONAL),
    ("bdr",    AssetType.BDR),
]

# Quantos resultados pedir por chamada (maximo da BRAPI)
_PAGE_LIMIT = 100


@dataclass
class SeedResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors:  int = 0
    by_type: dict[str, int] = field(default_factory=dict)


async def _fetch_all_for_type(brapi_type: str) -> list[dict]:
    """
    Busca todos os ativos de um tipo via BRAPI quote/list com paginacao.
    A BRAPI nao tem offset real, entao usamos busca em branco com limit maximo
    e verificamos se voltou o mesmo numero de resultados para inferir proxima pagina.
    """
    all_items: list[dict] = []
    seen_tickers: set[str] = set()
    page = 1
    while True:
        try:
            # fetch_ticker_suggestions aceita q="" para listar tudo do tipo
            items = await fetch_ticker_suggestions(
                q="",
                limit=_PAGE_LIMIT,
                asset_type=brapi_type,
            )
        except Exception as e:
            logger.error(f"[seed] erro ao buscar BRAPI type={brapi_type} page={page}: {e}")
            break

        if not items:
            break

        new_items = []
        for item in items:
            ticker = (
                item.get("stock")
                or item.get("ticker")
                or item.get("symbol")
                or ""
            ).strip().upper()
            if ticker and ticker not in seen_tickers:
                seen_tickers.add(ticker)
                new_items.append(item)

        all_items.extend(new_items)
        logger.info(f"[seed] type={brapi_type} page={page}: {len(new_items)} novos ({len(all_items)} acumulados)")

        # BRAPI nao tem paginacao real no /quote/list — se retornou menos que o limit, chegamos ao fim
        if len(items) < _PAGE_LIMIT:
            break
        page += 1

    return all_items


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


async def run_asset_seed(db: AsyncSession) -> SeedResult:
    """
    Ponto de entrada do seed. Recebe uma sessao de banco ja aberta.
    Faz commit em lotes de 200 para nao sobrecarregar a transacao.
    """
    result = SeedResult()
    BATCH_SIZE = 200
    batch_ops = 0

    for brapi_type, asset_type in _SEED_TYPES:
        type_label = asset_type.value
        result.by_type[type_label] = 0

        logger.info(f"[seed] iniciando tipo {type_label} (brapi_type={brapi_type})")
        items = await _fetch_all_for_type(brapi_type)
        logger.info(f"[seed] tipo {type_label}: {len(items)} ativos recebidos da BRAPI")

        for item in items:
            ticker = (
                item.get("stock")
                or item.get("ticker")
                or item.get("symbol")
                or ""
            ).strip().upper()
            if not ticker:
                result.errors += 1
                continue

            name   = (item.get("name") or item.get("longName") or "").strip()
            sector = (item.get("sector") or item.get("segment") or "").strip() or None

            try:
                status = await _upsert_asset(db, ticker, name, asset_type, sector)
                if status == "created":
                    result.created += 1
                    result.by_type[type_label] += 1
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
        f"{result.errors} erros"
    )
    return result
