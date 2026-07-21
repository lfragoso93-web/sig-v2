"""Serviço read-only do relatório de impacto da limpeza pré-produção.

O serviço reaproveita integralmente o inventário canônico e apenas converte suas
tabelas para o contrato de impacto. Nenhuma política é duplicada e nenhum SQL de
limpeza, exportação ou rebuild é executado por este módulo.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.pre_prod_cleanup_impact_contract import (
    IMPACT_REPORT_MODE,
    IMPACT_REPORT_SCHEMA_VERSION,
    CleanupImpactSafety,
    CleanupImpactTable,
    CleanupImpactTotals,
    PreProdCleanupImpactReport,
)
from app.services.pre_prod_inventory_service import (
    REPORT_SCHEMA_VERSION as INVENTORY_SCHEMA_VERSION,
    build_pre_prod_inventory,
)


async def build_pre_prod_cleanup_impact(
    *,
    branch: str,
    commit_sha: str,
    session: AsyncSession | None = None,
) -> PreProdCleanupImpactReport:
    """Constrói o dry-run de impacto a partir do inventário read-only.

    A sessão, quando fornecida, é encerrada por rollback pelo serviço de
    inventário. Isso mantém o mesmo comportamento de segurança já validado para
    o inventário pré-produção.
    """
    inventory = await build_pre_prod_inventory(session)
    if inventory.schema_version != INVENTORY_SCHEMA_VERSION:
        raise ValueError(
            "unsupported inventory schema for cleanup impact: "
            f"{inventory.schema_version!r}"
        )

    tables = [CleanupImpactTable.from_inventory(table) for table in inventory.tables]
    blockers = sorted(table.name for table in tables if table.blocked)

    return PreProdCleanupImpactReport(
        schema_version=IMPACT_REPORT_SCHEMA_VERSION,
        generated_at=inventory.generated_at,
        mode=IMPACT_REPORT_MODE,
        branch=branch,
        commit_sha=commit_sha,
        inventory_schema_version=inventory.schema_version,
        tables=tables,
        totals=CleanupImpactTotals.from_tables(tables),
        blockers=blockers,
        safety=CleanupImpactSafety(),
    )
