"""
Service para CRUD das metas de alocacao por classe de ativo.

Classes suportadas (VALID_ASSET_CLASSES)
=========================================
ACAO, FII, ETF_NACIONAL, ETF_INTERNACIONAL, STOCK, BDR, CRIPTO,
RENDA_FIXA, TESOURO_DIRETO, OUTRO

BDR foi adicionado explicitamente na Sprint 5E (Issue #79).
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.models.portfolio_class_target import PortfolioClassTarget
from decimal import Decimal
import math

# Todas as classes de ativos reconhecidas pelo sistema.
# BDR adicionado explicitamente na Sprint 5E.
VALID_ASSET_CLASSES: set[str] = {
    "ACAO",
    "FII",
    "ETF_NACIONAL",
    "ETF_INTERNACIONAL",
    "STOCK",
    "BDR",
    "CRIPTO",
    "RENDA_FIXA",
    "TESOURO_DIRETO",
    "OUTRO",
}

_TYPE_LABEL: dict[str, str] = {
    "ACAO": "Ações",
    "FII": "FIIs",
    "ETF_NACIONAL": "ETFs Nacionais",
    "ETF_INTERNACIONAL": "ETFs Internacionais",
    "STOCK": "Stocks",
    "BDR": "BDRs",
    "CRIPTO": "Criptomoedas",
    "RENDA_FIXA": "Renda Fixa",
    "TESOURO_DIRETO": "Tesouro Direto",
    "OUTRO": "Outros",
}


async def get_targets(
    db: AsyncSession,
    portfolio_id: int,
) -> list[PortfolioClassTarget]:
    result = await db.execute(
        select(PortfolioClassTarget).where(
            PortfolioClassTarget.portfolio_id == portfolio_id
        )
    )
    return list(result.scalars().all())


async def get_targets_map(
    db: AsyncSession,
    portfolio_id: int,
) -> dict[str, float]:
    """Retorna {asset_type: target_pct} para uso rapido no portfolio_service."""
    targets = await get_targets(db, portfolio_id)
    return {t.asset_type: float(t.target_pct) for t in targets}


async def get_targets_with_current(
    db: AsyncSession,
    portfolio_id: int,
    current_distribution: list[dict],
) -> list[dict]:
    """
    Retorna lista combinada de alocacao atual vs. alvo por classe.

    Parametros
    ----------
    current_distribution : lista retornada por get_asset_distribution()
        Cada item: {asset_type, label, value, percentage, color}

    Retorno
    -------
    Lista de dicts com:
        asset_type   : str
        label        : str
        target_pct   : float  (0 se nao configurado)
        current_pct  : float  (0 se nao ha posicao)
        delta_pct    : float  (current - target; positivo = sobrealocado)
        color        : str
    """
    targets_map = await get_targets_map(db, portfolio_id)

    # Monta mapa de distribuicao atual por asset_type
    current_map: dict[str, dict] = {
        d["asset_type"]: d for d in current_distribution
    }

    # Uniao de todas as classes que tem alvo OU posicao atual
    all_types = set(targets_map.keys()) | set(current_map.keys())

    rows: list[dict] = []
    for at in sorted(all_types):
        current_item = current_map.get(at, {})
        current_pct = current_item.get("percentage", 0.0)
        target_pct = targets_map.get(at, 0.0)
        rows.append({
            "asset_type": at,
            "label": _TYPE_LABEL.get(at, at.replace("_", " ").title()),
            "target_pct": round(float(target_pct), 2),
            "current_pct": round(float(current_pct), 2),
            "delta_pct": round(float(current_pct) - float(target_pct), 2),
            "color": current_item.get("color", "#6b7280"),
        })

    # Ordena: maior atual primeiro
    rows.sort(key=lambda r: r["current_pct"], reverse=True)
    return rows


async def upsert_target(
    db: AsyncSession,
    portfolio_id: int,
    asset_type: str,
    target_pct: float,
) -> PortfolioClassTarget:
    """Cria ou atualiza a meta de uma classe. Suporta todas as classes em VALID_ASSET_CLASSES."""
    normalized_type = str(asset_type).strip().upper()
    safe_pct = Decimal(str(round(float(target_pct), 2)))

    result = await db.execute(
        select(PortfolioClassTarget).where(
            PortfolioClassTarget.portfolio_id == portfolio_id,
            PortfolioClassTarget.asset_type == normalized_type,
        )
    )
    target = result.scalar_one_or_none()

    if target is None:
        target = PortfolioClassTarget(
            portfolio_id=portfolio_id,
            asset_type=normalized_type,
            target_pct=safe_pct,
        )
        db.add(target)
    else:
        target.target_pct = safe_pct

    await db.commit()
    await db.refresh(target)
    return target


async def bulk_upsert_targets(
    db: AsyncSession,
    portfolio_id: int,
    items: list[tuple[str, float]],
) -> list[PortfolioClassTarget]:
    """Atualiza múltiplas metas em uma única transação atômica."""
    if not items:
        return await get_targets(db, portfolio_id)

    for raw_type, raw_pct in items:
        normalized_type = str(raw_type).strip().upper()
        if not math.isfinite(float(raw_pct)) or float(raw_pct) < 0 or float(raw_pct) > 100:
            raise ValueError(f"target_pct inválido para {normalized_type}: deve estar entre 0 e 100.")
        safe_pct = Decimal(str(round(float(raw_pct), 2)))
        stmt = (
            pg_insert(PortfolioClassTarget)
            .values(
                portfolio_id=portfolio_id,
                asset_type=normalized_type,
                target_pct=safe_pct,
            )
            .on_conflict_do_update(
                constraint="uq_portfolio_class_target",
                set_={"target_pct": safe_pct},
            )
        )
        await db.execute(stmt)

    await db.commit()
    return await get_targets(db, portfolio_id)


async def delete_target(
    db: AsyncSession,
    portfolio_id: int,
    asset_type: str,
) -> bool:
    result = await db.execute(
        select(PortfolioClassTarget).where(
            PortfolioClassTarget.portfolio_id == portfolio_id,
            PortfolioClassTarget.asset_type == asset_type,
        )
    )
    target = result.scalar_one_or_none()
    if target is None:
        return False
    await db.delete(target)
    await db.commit()
    return True
