"""Definições canônicas de estágios do system-bootstrap.v4.

Inventário canônico com identificadores, nomes operacionais, descrições,
dependências e flags de provedores para a Central de Bootstrap SuperAdmin.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BootstrapStageDefinition:
    """Metadados de um estágio canônico de bootstrap."""

    id: str
    name: str
    description: str
    dependencies: tuple[str, ...]
    provider_dependent: bool
    destructive: bool


CANONICAL_BOOTSTRAP_STAGES: tuple[BootstrapStageDefinition, ...] = (
    BootstrapStageDefinition(
        id="b3_baseline",
        name="Catálogo e Histórico Base B3",
        description=(
            "Ingestão COTAHIST B3 e criação do catálogo base de ativos"
        ),
        dependencies=(),
        provider_dependent=False,
        destructive=False,
    ),
    BootstrapStageDefinition(
        id="asset_catalog",
        name="Enriquecimento BRAPI e Cripto",
        description="Enriquecimento de ações/FIIs via BRAPI e suporte Cripto",
        dependencies=("b3_baseline",),
        provider_dependent=True,
        destructive=False,
    ),
    BootstrapStageDefinition(
        id="treasury_catalog",
        name="Catálogo do Tesouro Direto",
        description="Sincronização dos títulos públicos federais oficiais",
        dependencies=(),
        provider_dependent=True,
        destructive=False,
    ),
    BootstrapStageDefinition(
        id="treasury_reconciliation",
        name="Reconciliação do Tesouro",
        description=(
            "Reconciliação e associação de transações do Tesouro Direto"
        ),
        dependencies=("treasury_catalog",),
        provider_dependent=False,
        destructive=False,
    ),
    BootstrapStageDefinition(
        id="treasury_history",
        name="Histórico Oficial do Tesouro",
        description="Reconstrução oficial de PU e taxas dos títulos públicos",
        dependencies=("treasury_catalog",),
        provider_dependent=True,
        destructive=True,
    ),
    BootstrapStageDefinition(
        id="asset_price_history",
        name="Preços Históricos Cripto",
        description=(
            "Carga histórica de cotações para ativos Cripto suportados"
        ),
        dependencies=("asset_catalog",),
        provider_dependent=True,
        destructive=False,
    ),
    BootstrapStageDefinition(
        id="benchmarks",
        name="Séries Históricas de Benchmarks",
        description="Carga histórica de CDI, SELIC, IPCA e IBOVESPA",
        dependencies=(),
        provider_dependent=True,
        destructive=False,
    ),
    BootstrapStageDefinition(
        id="fx_rates",
        name="Taxas de Câmbio PTAX",
        description="Carga de cotações oficiais BACEN PTAX (USD, EUR, etc.)",
        dependencies=(),
        provider_dependent=True,
        destructive=False,
    ),
    BootstrapStageDefinition(
        id="asset_dividends",
        name="Proventos Globais de Ativos",
        description="Sincronização de proventos sob gate operacional #226",
        dependencies=("asset_catalog",),
        provider_dependent=True,
        destructive=False,
    ),
    BootstrapStageDefinition(
        id="corporate_events",
        name="Eventos Corporativos Globais",
        description="Sincronização de eventos corporativos sob gate #158",
        dependencies=("asset_catalog",),
        provider_dependent=True,
        destructive=False,
    ),
    BootstrapStageDefinition(
        id="asset_fundamentals",
        name="Fundamentos e Indicadores de Ativos",
        description=(
            "Coleta e pré-aquecimento de indicadores fundamentalistas, "
            "métricas cripto e títulos públicos"
        ),
        dependencies=("asset_catalog", "treasury_catalog"),
        provider_dependent=True,
        destructive=False,
    ),
)
