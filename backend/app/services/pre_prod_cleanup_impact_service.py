"""Serviço read-only do relatório de impacto da limpeza pré-produção.

O serviço reaproveita integralmente o inventário canônico, descobre as foreign
keys no mesmo snapshot transacional e produz um plano auditável. Nenhum SQL de
limpeza, exportação ou rebuild é executado por este módulo.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.services.pre_prod_cleanup_impact_contract import (
    IMPACT_REPORT_MODE,
    IMPACT_REPORT_SCHEMA_VERSION,
    CleanupImpactDependency,
    CleanupImpactDependencyPlan,
    CleanupImpactSafety,
    CleanupImpactTable,
    CleanupImpactTotals,
    PreProdCleanupImpactReport,
)
from app.services.pre_prod_dependency_graph import TableDependencyGraph
from app.services.pre_prod_dependency_introspection import (
    discover_table_dependencies,
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
    rollback_supplied_session: bool = True,
) -> PreProdCleanupImpactReport:
    """Constrói o dry-run no mesmo snapshot read-only de inventário e FKs.

    Quando uma sessão é fornecida, o chamador pode preservar a transação para
    compartilhar exatamente o mesmo snapshot com a exportação auditável.
    """
    owns_session = session is None
    active_session = session or AsyncSessionLocal()

    try:
        inventory = await build_pre_prod_inventory(
            active_session,
            rollback_supplied_session=False,
        )
        if inventory.schema_version != INVENTORY_SCHEMA_VERSION:
            raise ValueError(
                "unsupported inventory schema for cleanup impact: "
                f"{inventory.schema_version!r}"
            )

        tables = [
            CleanupImpactTable.from_inventory(table) for table in inventory.tables
        ]
        table_names = [table.name for table in tables]
        dependencies = await discover_table_dependencies(
            active_session,
            tables=table_names,
        )
        graph_plan = TableDependencyGraph(
            tables=table_names,
            dependencies=dependencies,
        ).build_plan()

        export_required = {
            table.name
            for table in tables
            if table.proposed_action == "export_required"
        }
        rebuildable = {
            table.name
            for table in tables
            if table.proposed_action == "clean_and_rebuild"
        }
        cleanable = export_required | rebuildable

        dependency_plan = CleanupImpactDependencyPlan(
            dependencies=[
                CleanupImpactDependency(
                    dependent=edge.dependent,
                    dependency=edge.dependency,
                    constraint_name=edge.constraint_name,
                )
                for edge in dependencies
            ],
            cleanup_order=[
                table for table in graph_plan.cleanup_order if table in cleanable
            ],
            rebuild_order=[
                table for table in graph_plan.rebuild_order if table in rebuildable
            ],
            export_required_before_cleanup=sorted(export_required),
            cycles=graph_plan.cycles,
        )

        blockers = sorted(
            [table.name for table in tables if table.blocked]
            + ["referential_cycle:" + "->".join(cycle) for cycle in graph_plan.cycles]
        )

        return PreProdCleanupImpactReport(
            schema_version=IMPACT_REPORT_SCHEMA_VERSION,
            generated_at=inventory.generated_at,
            mode=IMPACT_REPORT_MODE,
            branch=branch,
            commit_sha=commit_sha,
            inventory_schema_version=inventory.schema_version,
            tables=tables,
            totals=CleanupImpactTotals.from_tables(tables),
            dependency_plan=dependency_plan,
            blockers=blockers,
            safety=CleanupImpactSafety(),
        )
    finally:
        if owns_session or rollback_supplied_session:
            await active_session.rollback()
        if owns_session:
            await active_session.close()
