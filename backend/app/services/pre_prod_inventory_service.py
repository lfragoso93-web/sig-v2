"""Inventário read-only para o rebuild canônico de pré-produção.

O serviço executa somente consultas ``SELECT`` e sempre encerra a sessão com
rollback. Ele não importa nem reutiliza serviços de rebuild para impedir efeitos
colaterais durante o dry-run.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal

REPORT_SCHEMA_VERSION = "pre-prod-inventory.v2"
_SAFE_IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]*$")

TABLE_POLICIES: dict[str, tuple[str, str]] = {
    "alembic_version": (
        "preserved",
        "Controle estrutural das migrations aplicadas; nunca deve ser reconstruído pelo rebuild de dados.",
    ),
    "app_configs": (
        "preserved",
        "Configuração funcional persistida da aplicação.",
    ),
    "audit_logs": (
        "preserved",
        "Trilha histórica de auditoria que não pode ser regenerada.",
    ),
    "goal_allocations": (
        "preserved",
        "Alocações definidas pelo usuário para metas financeiras.",
    ),
    "goals": (
        "preserved",
        "Metas financeiras definidas pelo usuário.",
    ),
    "irpf_losses": (
        "preserved",
        "Saldos fiscais históricos e prejuízos acumulados informados ou apurados.",
    ),
    "irpf_records": (
        "preserved",
        "Registros fiscais associados ao histórico da carteira.",
    ),
    "irpf_reports": (
        "preserved",
        "Relatórios fiscais emitidos que devem permanecer rastreáveis.",
    ),
    "portfolio_class_targets": (
        "preserved",
        "Metas de alocação configuradas pelo usuário.",
    ),
    "portfolios": (
        "preserved",
        "Entidade principal da carteira e seus metadados.",
    ),
    "system_configs": (
        "preserved",
        "Configuração operacional persistida do sistema.",
    ),
    "users": (
        "preserved",
        "Identidades e credenciais dos usuários.",
    ),
    "corporate_events": (
        "export_before_cleanup",
        "Eventos podem conter estado aplicado, vínculo com carteira e dados brutos não integralmente reproduzíveis.",
    ),
    "fixed_income_investments": (
        "export_before_cleanup",
        "Investimentos de renda fixa contêm condições contratuais informadas pelo usuário.",
    ),
    "transactions": (
        "export_before_cleanup",
        "Livro-razão financeiro informado pelo usuário e fonte dos rebuilds posteriores.",
    ),
    "asset_aliases": (
        "rebuildable",
        "Aliases canônicos podem ser recriados a partir do catálogo e dos eventos corporativos exportados.",
    ),
    "asset_dividends": (
        "rebuildable",
        "Catálogo global de eventos pode ser novamente coletado e normalizado.",
    ),
    "asset_prices": (
        "rebuildable",
        "Histórico de preços possui fontes oficiais e rotinas idempotentes de seed.",
    ),
    "assets": (
        "rebuildable",
        "Catálogo canônico é reconstruído pelas fontes oficiais e reconciliado com as transações exportadas.",
    ),
    "dividends": (
        "rebuildable",
        "Direitos legados serão descartados e reconstruídos sob demanda a partir de eventos e transações.",
    ),
    "dividends_sync_jobs": (
        "rebuildable",
        "Estado técnico de sincronização pode ser reiniciado após o seed.",
    ),
    "fx_rates": (
        "rebuildable",
        "Cache de cotações PTAX é idempotente e regenerável pela fonte oficial.",
    ),
    "portfolio_class_snapshots": (
        "rebuildable",
        "Snapshots por classe são derivados de transações, posições e preços persistidos.",
    ),
    "portfolio_positions": (
        "rebuildable",
        "Posições são projeções derivadas do livro de transações.",
    ),
    "portfolio_snapshots": (
        "rebuildable",
        "Snapshots consolidados são derivados de transações, posições, preços e proventos.",
    ),
    "rate_history": (
        "rebuildable",
        "Séries macroeconômicas são regeneráveis por fontes oficiais.",
    ),
}


@dataclass(frozen=True)
class TableInventory:
    name: str
    classification: str
    rationale: str
    row_count: int


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    count: int
    description: str


@dataclass(frozen=True)
class PreProdInventoryReport:
    schema_version: str
    generated_at: str
    mode: str
    database_dialect: str
    tables: list[TableInventory]
    findings: list[Finding]
    totals: dict[str, int]
    safety: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _table_policy(name: str) -> tuple[str, str]:
    return TABLE_POLICIES.get(
        name,
        (
            "unclassified",
            "Tabela desconhecida para esta versão da política; exige revisão arquitetural antes de qualquer limpeza.",
        ),
    )


def _classify_table(name: str) -> str:
    return _table_policy(name)[0]


def _quote_identifier(name: str) -> str:
    if not _SAFE_IDENTIFIER.fullmatch(name):
        raise ValueError(f"unsafe SQL identifier: {name!r}")
    return f'"{name}"'


async def _table_names(session: AsyncSession, dialect: str) -> list[str]:
    if dialect == "sqlite":
        result = await session.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        )
    else:
        result = await session.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
                "ORDER BY table_name"
            )
        )
    return [str(row[0]) for row in result]


async def _row_count(session: AsyncSession, table_name: str) -> int:
    quoted = _quote_identifier(table_name)
    result = await session.execute(text(f"SELECT COUNT(*) FROM {quoted}"))
    return int(result.scalar_one())


async def _scalar_count(session: AsyncSession, sql: str) -> int:
    result = await session.execute(text(sql))
    return int(result.scalar_one())


async def _canonical_findings(
    session: AsyncSession,
    available_tables: set[str],
) -> list[Finding]:
    findings: list[Finding] = []

    if "asset_aliases" in available_tables:
        duplicate_aliases = await _scalar_count(
            session,
            """
            SELECT COUNT(*) FROM (
                SELECT LOWER(alias_ticker), asset_type
                FROM asset_aliases
                GROUP BY LOWER(alias_ticker), asset_type
                HAVING COUNT(*) > 1
            ) duplicated
            """,
        )
        findings.append(
            Finding(
                code="duplicate_asset_aliases",
                severity="error" if duplicate_aliases else "info",
                count=duplicate_aliases,
                description="Aliases duplicados por ticker normalizado e tipo de ativo.",
            )
        )

    if {"asset_aliases", "assets"}.issubset(available_tables):
        orphan_aliases = await _scalar_count(
            session,
            """
            SELECT COUNT(*)
            FROM asset_aliases aa
            LEFT JOIN assets a ON a.id = aa.asset_id
            WHERE a.id IS NULL
            """,
        )
        findings.append(
            Finding(
                code="orphan_asset_aliases",
                severity="error" if orphan_aliases else "info",
                count=orphan_aliases,
                description="Aliases sem ativo canônico correspondente.",
            )
        )

    if {"asset_prices", "assets"}.issubset(available_tables):
        orphan_prices = await _scalar_count(
            session,
            """
            SELECT COUNT(*)
            FROM asset_prices ap
            LEFT JOIN assets a ON a.id = ap.asset_id
            WHERE a.id IS NULL
            """,
        )
        findings.append(
            Finding(
                code="orphan_asset_prices",
                severity="error" if orphan_prices else "info",
                count=orphan_prices,
                description="Preços históricos sem ativo canônico correspondente.",
            )
        )

        duplicate_prices = await _scalar_count(
            session,
            """
            SELECT COUNT(*) FROM (
                SELECT asset_id, timestamp
                FROM asset_prices
                GROUP BY asset_id, timestamp
                HAVING COUNT(*) > 1
            ) duplicated
            """,
        )
        findings.append(
            Finding(
                code="duplicate_asset_prices",
                severity="error" if duplicate_prices else "info",
                count=duplicate_prices,
                description="Preços duplicados para o mesmo ativo e timestamp.",
            )
        )

    if "portfolio_snapshots" in available_tables:
        duplicate_snapshots = await _scalar_count(
            session,
            """
            SELECT COUNT(*) FROM (
                SELECT portfolio_id, snapshot_date
                FROM portfolio_snapshots
                GROUP BY portfolio_id, snapshot_date
                HAVING COUNT(*) > 1
            ) duplicated
            """,
        )
        findings.append(
            Finding(
                code="duplicate_portfolio_snapshots",
                severity="error" if duplicate_snapshots else "info",
                count=duplicate_snapshots,
                description="Snapshots consolidados duplicados por carteira e data.",
            )
        )

    return findings


async def build_pre_prod_inventory(
    session: AsyncSession | None = None,
    *,
    rollback_supplied_session: bool = True,
) -> PreProdInventoryReport:
    """Gera inventário read-only e devolve um relatório JSON serializável.

    O chamador pode manter uma transação read-only fornecida aberta para compartilhar
    o mesmo snapshot com outra ferramenta PostgreSQL. Sessões criadas pelo serviço
    continuam sempre encerradas por rollback.
    """
    owns_session = session is None
    active_session = session or AsyncSessionLocal()

    try:
        bind = active_session.get_bind()
        dialect = bind.dialect.name
        names = await _table_names(active_session, dialect)

        tables: list[TableInventory] = []
        for name in names:
            classification, rationale = _table_policy(name)
            tables.append(
                TableInventory(
                    name=name,
                    classification=classification,
                    rationale=rationale,
                    row_count=await _row_count(active_session, name),
                )
            )

        findings = await _canonical_findings(active_session, set(names))

        totals = {
            "tables": len(tables),
            "rows": sum(item.row_count for item in tables),
            "preserved_tables": sum(
                item.classification == "preserved" for item in tables
            ),
            "export_tables": sum(
                item.classification == "export_before_cleanup" for item in tables
            ),
            "rebuildable_tables": sum(
                item.classification == "rebuildable" for item in tables
            ),
            "unclassified_tables": sum(
                item.classification == "unclassified" for item in tables
            ),
            "blocking_findings": sum(
                item.count for item in findings if item.severity == "error"
            ),
        }

        return PreProdInventoryReport(
            schema_version=REPORT_SCHEMA_VERSION,
            generated_at=datetime.now(timezone.utc).isoformat(),
            mode="dry-run",
            database_dialect=dialect,
            tables=tables,
            findings=findings,
            totals=totals,
            safety={
                "read_only": True,
                "writes_executed": 0,
                "cleanup_executed": False,
                "rebuild_executed": False,
            },
        )
    finally:
        if owns_session or rollback_supplied_session:
            await active_session.rollback()
        if owns_session:
            await active_session.close()
