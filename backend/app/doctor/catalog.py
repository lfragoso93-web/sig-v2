"""Catálogo inicial de invariantes arquiteturais já protegidos no SGI."""

from __future__ import annotations

from types import MappingProxyType

from app.doctor.contracts import DoctorCatalogEntry, DoctorCheckKind, DoctorSeverity


ARCHITECTURE_CHECKS = (
    DoctorCatalogEntry(
        finding_id="SGI001",
        title="Alembic e MetaData convergem dentro da política explícita",
        severity=DoctorSeverity.ERROR,
        kind=DoctorCheckKind.DATABASE,
        evidence=(
            "backend/app/governance/alembic_drift_gate.py",
            "backend/tests/test_alembic_drift_gate.py",
            "backend/tests/test_alembic_revision_integrity.py",
        ),
    ),
    DoctorCatalogEntry(
        finding_id="SGI002",
        title="ORM legado e seus imports não retornam ao runtime",
        severity=DoctorSeverity.ERROR,
        kind=DoctorCheckKind.STATIC,
        evidence=(
            "backend/tests/test_alembic_legacy_schema_presence_guard.py",
            "backend/tests/test_removed_model_consumers_and_main_import.py",
        ),
    ),
    DoctorCatalogEntry(
        finding_id="SGI003",
        title="Transações usam o writer canônico",
        severity=DoctorSeverity.ERROR,
        kind=DoctorCheckKind.BEHAVIORAL,
        evidence=("backend/tests/test_transaction_write_service.py",),
    ),
    DoctorCatalogEntry(
        finding_id="SGI004",
        title="PortfolioSnapshot mantém um único writer canônico",
        severity=DoctorSeverity.ERROR,
        kind=DoctorCheckKind.STATIC,
        evidence=("backend/tests/test_portfolio_snapshot_single_writer_policy.py",),
    ),
    DoctorCatalogEntry(
        finding_id="SGI005",
        title="Dividendos permanecem vinculados ao ativo canônico",
        severity=DoctorSeverity.ERROR,
        kind=DoctorCheckKind.STATIC,
        evidence=(
            "backend/tests/test_no_legacy_dividend_relationships.py",
            "backend/tests/test_transactions_no_dividend_materialization.py",
        ),
    ),
    DoctorCatalogEntry(
        finding_id="SGI006",
        title="Eventos corporativos permanecem fail-closed",
        severity=DoctorSeverity.ERROR,
        kind=DoctorCheckKind.BEHAVIORAL,
        evidence=(
            "backend/tests/test_corporate_event_reconciliation_plan.py",
            "backend/tests/test_corporate_event_reconciliation_matched_writer.py",
        ),
    ),
    DoctorCatalogEntry(
        finding_id="SGI007",
        title="Leituras financeiras preservam fronteiras DB-first",
        severity=DoctorSeverity.ERROR,
        kind=DoctorCheckKind.STATIC,
        evidence=(
            "backend/tests/test_fx_runtime_db_first_boundary.py",
            "backend/tests/test_portfolio_snapshot_twr_db_first_price_boundary.py",
        ),
    ),
    DoctorCatalogEntry(
        finding_id="SGI008",
        title="Bootstrap preserva idempotência",
        severity=DoctorSeverity.ERROR,
        kind=DoctorCheckKind.BEHAVIORAL,
        evidence=(
            "backend/tests/test_bootstrap_remaining_idempotency.py",
            "backend/tests/test_bootstrap_benchmark_and_corporate_event_idempotency.py",
        ),
    ),
    DoctorCatalogEntry(
        finding_id="SGI009",
        title="Código removido não possui consumidores ativos",
        severity=DoctorSeverity.ERROR,
        kind=DoctorCheckKind.STATIC,
        evidence=(
            "backend/tests/test_removed_model_consumers_and_main_import.py",
            "backend/tests/test_removed_corporate_event_legacy_tooling.py",
        ),
    ),
    DoctorCatalogEntry(
        finding_id="SGI010",
        title="Readiness permanece explícito e fail-closed",
        severity=DoctorSeverity.ERROR,
        kind=DoctorCheckKind.BEHAVIORAL,
        evidence=(
            "backend/tests/test_system_readiness_contract.py",
            "backend/tests/test_user_test_readiness_service.py",
        ),
    ),
    DoctorCatalogEntry(
        finding_id="SGI011",
        title="Runtime declara identidade de commit verificável",
        severity=DoctorSeverity.ERROR,
        kind=DoctorCheckKind.RUNTIME,
        evidence=(
            "backend/tests/test_compose_runtime_commit_identity.py",
            "backend/tests/test_asset_bootstrap_execution_identity.py",
        ),
    ),
    DoctorCatalogEntry(
        finding_id="SGI012",
        title="Agent Skills versionadas cobrem os contratos do SGI",
        severity=DoctorSeverity.ERROR,
        kind=DoctorCheckKind.STATIC,
        evidence=("backend/tests/test_agent_skills_contract.py",),
    ),
    DoctorCatalogEntry(
        finding_id="SGI013",
        title="Runtime deterministico valida clock, config e query budgets",
        severity=DoctorSeverity.ERROR,
        kind=DoctorCheckKind.BEHAVIORAL,
        evidence=("backend/tests/test_deterministic_runtime_contract.py",),
    ),
    DoctorCatalogEntry(
        finding_id="SGI014",
        title="Acesso sensivel por carteira exige contexto explicito",
        severity=DoctorSeverity.ERROR,
        kind=DoctorCheckKind.BEHAVIORAL,
        evidence=("backend/tests/test_portfolio_access_context.py",),
    ),
)

architecture_check_by_id = MappingProxyType(
    {entry.finding_id: entry for entry in ARCHITECTURE_CHECKS}
)
