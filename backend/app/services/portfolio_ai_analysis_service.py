from __future__ import annotations

import logging
import time
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.portfolio_ai_analysis import (
    AiExplanationMetadata,
    AiQuestionResponse,
    ClassContributionAllocation,
    ContributionScenarioDto,
    ContributionSimulationResponse,
    PortfolioAiAnalysisResponse,
)
from app.schemas.portfolio_analysis import (
    ClassAnalysisDetail,
    PortfolioConsolidatedAnalysisResponse,
    RebalanceAction,
)
from app.services.portfolio_analysis_service import PortfolioAnalysisService

logger = logging.getLogger(__name__)


class AiExplainerProvider(Protocol):
    async def explain_analysis(
        self, analysis: PortfolioConsolidatedAnalysisResponse
    ) -> PortfolioAiAnalysisResponse: ...

    async def explain_simulation(
        self,
        analysis: PortfolioConsolidatedAnalysisResponse,
        amount: float,
        allocations: list[ClassContributionAllocation],
    ) -> str: ...

    async def answer_question(
        self, analysis: PortfolioConsolidatedAnalysisResponse, question: str
    ) -> tuple[str, list[str]]: ...


class DeterministicAuditExplainer:
    """Provedor determinístico e auditável de explicações e insights de IA.

    Garante conformidade com o princípio de não-alucinação: todo texto é
    ancorado estritamente nos números consolidados do DTO estruturado.
    """

    provider_name = "sgi-audit-explainer-v1"
    model_name = "deterministic-rule-engine"

    def _determine_posture(self, classes: list[ClassAnalysisDetail]) -> tuple[str, str]:
        weights = {c.asset_type.lower(): c.allocation.current_weight_pct for c in classes}
        rf_weight = weights.get("renda_fixa", 0.0) + weights.get("tesouro_direto", 0.0)
        rv_weight = weights.get("acoes", 0.0) + weights.get("stocks", 0.0)
        fii_weight = weights.get("fiis", 0.0) + weights.get("reits", 0.0)

        if rf_weight >= 60.0:
            return (
                "Conservadora e Focada em Preservação",
                f"A carteira apresenta um perfil predominantemente defensivo, com {rf_weight:.1f}% alocado "
                "em Renda Fixa e Títulos Públicos, priorizando segurança e liquidez.",
            )
        elif rv_weight >= 50.0:
            return (
                "Arrojada com Foco em Crescimento",
                f"A carteira adota uma postura arrojada orientada ao longo prazo, com {rv_weight:.1f}% em "
                "Ações e ativos de volatilidade, buscando ganho de capital e valorização.",
            )
        elif fii_weight >= 40.0:
            return (
                "Orientada à Renda Passiva",
                f"A estratégia é centrada na geração constante de fluxo de caixa, com {fii_weight:.1f}% "
                "distribuído em Fundos Imobiliários e ativos geradores de proventos.",
            )
        else:
            return (
                "Equilibrada e Multiclasse",
                "A alocação distribui o capital harmoniosamente entre Renda Fixa, Ações e FIIs, "
                "balanceando preservação de patrimônio, dividendos e potencial de valorização.",
            )

    def _generate_strengths(self, analysis: PortfolioConsolidatedAnalysisResponse) -> list[str]:
        strengths: list[str] = []

        if analysis.overall_health_score >= 80:
            strengths.append(
                f"Score de saúde alto ({analysis.overall_health_score}/100), indicando excelente aderência às metas estratégicas."
            )
        elif analysis.overall_health_score >= 60:
            strengths.append(
                f"Score de saúde moderado ({analysis.overall_health_score}/100), mantendo a carteira dentro de faixas operacionais seguras."
            )

        if analysis.classes_analyzed_count >= 3:
            strengths.append(
                f"Diversificação ampla entre {analysis.classes_analyzed_count} classes patrimoniais ativas."
            )

        balanced_classes = [
            c.label for c in analysis.classes
            if c.concentration.risk_level.value in ("low", "balanced")
        ]
        if balanced_classes:
            strengths.append(
                f"Nível de concentração saudável e controlado nas classes: {', '.join(balanced_classes)}."
            )

        income_classes = [
            c.label for c in analysis.classes
            if c.income.is_applicable and c.income.total_proventos > 0
        ]
        if income_classes:
            strengths.append(
                f"Fluxo recorrente de proventos ativo gerado por: {', '.join(income_classes)}."
            )

        return strengths or ["Carteira estruturada com classes ativas registradas."]

    def _generate_attention_points(self, analysis: PortfolioConsolidatedAnalysisResponse) -> list[str]:
        points: list[str] = []

        for c in analysis.classes:
            if c.concentration.risk_level.value in ("warning", "critical"):
                top_asset_text = (
                    f" (maior ativo {c.concentration.top_asset.ticker} com {c.concentration.top_asset.weight_in_class_pct:.1f}% da classe)"
                    if c.concentration.top_asset
                    else ""
                )
                points.append(
                    f"Concentração elevada em {c.label}: risco classificado como '{c.concentration.risk_label}'{top_asset_text}."
                )

            if c.allocation.rebalance_action == RebalanceAction.BUY and c.allocation.gap_weight_pct:
                points.append(
                    f"Subalocação em {c.label}: está {abs(c.allocation.gap_weight_pct):.1f}% abaixo da meta estratégica planejada."
                )
            elif c.allocation.rebalance_action == RebalanceAction.REDUCE and c.allocation.gap_weight_pct:
                points.append(
                    f"Sobrealocação em {c.label}: ultrapassa a meta em {c.allocation.gap_weight_pct:.1f}% devido à valorização recente."
                )

            if c.fixed_income.is_applicable and c.fixed_income.maturing_next_12m_pct:
                if c.fixed_income.maturing_next_12m_pct >= 25.0:
                    points.append(
                        f"Liquidez em {c.label}: {c.fixed_income.maturing_next_12m_pct:.1f}% do valor total vence nos próximos 12 meses."
                    )

        if not points:
            points.append("Nenhum desvio crítico detectado. Todas as classes operam próximas às metas definidas.")

        return points

    def _generate_rebalancing_strategy(self, analysis: PortfolioConsolidatedAnalysisResponse) -> str:
        priority_classes = analysis.rebalance_priority_classes
        if not priority_classes:
            return (
                "A carteira está perfeitamente alinhada com as metas estipuladas. "
                "Para novos aportes, recomenda-se distribuir proporcionalmente conforme as metas percentuais estabelecidas."
            )

        buy_classes = [
            c.label for c in analysis.classes if c.allocation.rebalance_action == RebalanceAction.BUY
        ]
        reduce_classes = [
            c.label for c in analysis.classes if c.allocation.rebalance_action == RebalanceAction.REDUCE
        ]

        strategy_parts = []
        if buy_classes:
            strategy_parts.append(
                f"Direcionar 100% dos novos aportes e dividendos reinvestidos para as classes subalocadas: {', '.join(buy_classes)}."
            )
        if reduce_classes:
            strategy_parts.append(
                f"Evitar novos aportes imediatos em {', '.join(reduce_classes)}, permitindo que o crescimento das demais classes reequilibre a fatia sem necessidade de alienação forçada com tributação de IRPF."
            )

        return " ".join(strategy_parts)

    def _generate_scenarios(self, analysis: PortfolioConsolidatedAnalysisResponse) -> list[ContributionScenarioDto]:
        scenarios: list[ContributionScenarioDto] = []
        priority_class = analysis.max_divergence_class or (
            analysis.rebalance_priority_classes[0] if analysis.rebalance_priority_classes else "Aporte Geral"
        )

        for amt in [1000.0, 5000.0, 10000.0]:
            scenarios.append(
                ContributionScenarioDto(
                    amount=amt,
                    description=f"Aporte estratégico de R$ {amt:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    priority_class=priority_class,
                    estimated_gap_reduction=f"Reduz a divergência em {priority_class} e eleva o score de saúde da carteira.",
                )
            )
        return scenarios

    async def explain_analysis(
        self, analysis: PortfolioConsolidatedAnalysisResponse
    ) -> PortfolioAiAnalysisResponse:
        start_time = time.perf_counter()

        posture_label, posture_summary = self._determine_posture(analysis.classes)
        strengths = self._generate_strengths(analysis)
        attention_points = self._generate_attention_points(analysis)
        rebalance_strategy = self._generate_rebalancing_strategy(analysis)
        scenarios = self._generate_scenarios(analysis)

        exec_summary = (
            f"A carteira '{analysis.portfolio_name}' possui patrimônio consolidado de "
            f"R$ {analysis.total_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            + f" com Score de Alocação de {analysis.overall_health_score}/100. "
            f"Classificada com postura {posture_label.lower()}, sua prioridade imediata "
            f"é {('rebalancear ' + ', '.join(analysis.rebalance_priority_classes)) if analysis.rebalance_priority_classes else 'manter a disciplina de aportes regulares'}."
        )

        elapsed = (time.perf_counter() - start_time) * 1000

        return PortfolioAiAnalysisResponse(
            portfolio_id=analysis.portfolio_id,
            portfolio_name=analysis.portfolio_name,
            reference_date=analysis.reference_date,
            overall_health_score=analysis.overall_health_score,
            posture_label=posture_label,
            posture_summary=posture_summary,
            executive_summary=exec_summary,
            key_strengths=strengths,
            attention_points=attention_points,
            rebalancing_strategy=rebalance_strategy,
            contribution_scenarios=scenarios,
            metadata=AiExplanationMetadata(
                provider=self.provider_name,
                model=self.model_name,
                is_mock_or_deterministic=True,
                execution_time_ms=round(elapsed, 2),
            ),
        )

    async def explain_simulation(
        self,
        analysis: PortfolioConsolidatedAnalysisResponse,
        amount: float,
        allocations: list[ClassContributionAllocation],
    ) -> str:
        allocated_classes = [a.label for a in allocations if a.allocated_amount > 0]
        if not allocated_classes:
            return (
                f"O aporte de R$ {amount:,.2f} pode ser distribuído proporcionalmente "
                "entre as metas existentes, pois não há classes com desvio negativo expressivo."
            )

        top_alloc = max(allocations, key=lambda a: a.allocated_amount)
        return (
            f"Para o aporte simulado de R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            + f", o algoritmo de otimização recomenda direcionar a maior fatia para {top_alloc.label} "
            f"(R$ {top_alloc.allocated_amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            + f"), elevando sua participação para {top_alloc.projected_weight_pct:.1f}% e "
            f"recompondo a distância para a meta estratégica."
        )

    async def answer_question(
        self, analysis: PortfolioConsolidatedAnalysisResponse, question: str
    ) -> tuple[str, list[str]]:
        q_lower = question.lower()
        referenced_metrics: list[str] = []

        if any(w in q_lower for w in ["score", "saúde", "saude", "nota", "classificação", "classificacao"]):
            referenced_metrics.extend(["overall_health_score", "classes_analyzed_count"])
            ans = (
                f"O Score de Alocação da sua carteira é {analysis.overall_health_score}/100. "
                "Ele reflete a proximidade atual das suas posições em relação às metas percentuais definidas. "
                "Para elevar seu score, concentre os próximos aportes nas classes identificadas com desvio negativo "
                f"({', '.join(analysis.rebalance_priority_classes) if analysis.rebalance_priority_classes else 'nenhuma classe prioritária pendente'})."
            )
        elif any(w in q_lower for w in ["concentração", "concentracao", "risco", "ativo", "top"]):
            referenced_metrics.extend(["concentration.risk_level", "top_asset"])
            critical = [
                f"{c.label} ({c.concentration.top_asset.ticker if c.concentration.top_asset else 'ativo'} com {c.concentration.top_asset.weight_in_class_pct:.1f}% da classe)"
                for c in analysis.classes
                if c.concentration.top_asset and c.concentration.risk_level.value in ("warning", "critical")
            ]
            if critical:
                ans = (
                    "Identificamos pontos de atenção de concentração nas seguintes classes: "
                    + "; ".join(critical)
                    + ". Recomenda-se diversificar essas classes adicionando novos ativos qualificados antes de aumentar posição no líder."
                )
            else:
                ans = "A carteira apresenta um perfil de concentração saudável em todas as classes ativas, sem dependência excessiva de um único ativo."
        elif any(w in q_lower for w in ["aporte", "rebalancear", "rebalanceamento", "comprar", "prioridade"]):
            referenced_metrics.extend(["rebalance_priority_classes", "gap_weight_pct", "allocation.rebalance_action"])
            if analysis.rebalance_priority_classes:
                ans = (
                    f"A prioridade máxima para novos aportes é a classe {analysis.max_divergence_class or analysis.rebalance_priority_classes[0]}. "
                    f"Ao alocar novos recursos nela, você reduz o gap de alocação de forma gradual, sem precisar vender ativos valorizados nem pagar IR."
                )
            else:
                ans = "Todas as classes estão equilibradas dentro das faixas aceitáveis. Você pode distribuir seus novos aportes proporcionalmente às metas cadastradas."
        elif any(w in q_lower for w in ["provento", "dividendo", "renda", "dy"]):
            referenced_metrics.extend(["income.total_proventos", "income.weighted_dy_pct"])
            income_classes = [c for c in analysis.classes if c.income.is_applicable and c.income.total_proventos > 0]
            if income_classes:
                details = [f"{c.label} (total de R$ {c.income.total_proventos:,.2f})".replace(",", "X").replace(".", ",").replace("X", ".") for c in income_classes]
                ans = (
                    "Sua carteira possui geração de proventos ativa em: "
                    + ", ".join(details)
                    + ". O reinvestimento automático desses dividendos é uma ferramenta poderosa para acelerar o rebalanceamento natural."
                )
            else:
                ans = "Ainda não foram registrados proventos expressivos no período analisado para esta carteira."
        else:
            referenced_metrics.append("total_value")
            referenced_metrics.append("overall_health_score")
            ans = (
                f"Sua carteira consolida um patrimônio de R$ {analysis.total_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                + f" distribuído em {analysis.classes_analyzed_count} classes com score {analysis.overall_health_score}/100. "
                "Para uma análise mais detalhada sobre aportes, riscos ou proventos, sinta-se à vontade para perguntar especificamente sobre rebalanceamento ou concentração."
            )

        return ans, referenced_metrics


class PortfolioAiAnalysisService:
    """Serviço da Camada de IA explicável e governada para análise de carteiras."""

    def __init__(
        self,
        db: AsyncSession,
        explainer: AiExplainerProvider | None = None,
    ) -> None:
        self.db = db
        self.analysis_service = PortfolioAnalysisService(db)
        self.explainer = explainer or DeterministicAuditExplainer()

    async def get_ai_analysis(
        self, portfolio_id: int, user_id: int
    ) -> PortfolioAiAnalysisResponse:
        analysis = await self.analysis_service.get_portfolio_analysis(portfolio_id, user_id)
        return await self.explainer.explain_analysis(analysis)

    async def simulate_contribution(
        self, portfolio_id: int, user_id: int, amount: float
    ) -> ContributionSimulationResponse:
        start_time = time.perf_counter()
        analysis = await self.analysis_service.get_portfolio_analysis(portfolio_id, user_id)

        current_total = analysis.total_value
        projected_total = current_total + amount

        # Identificar classes com déficit (gap_value < 0 ou ação BUY)
        deficit_classes: list[tuple[ClassAnalysisDetail, float]] = []
        for c in analysis.classes:
            target_val = c.allocation.target_value
            if target_val is not None:
                # Se o valor atual é menor que a meta ideal no novo total
                ideal_in_projected = projected_total * ((c.allocation.target_weight_pct or 0.0) / 100.0)
                deficit = ideal_in_projected - c.allocation.current_value
                if deficit > 0:
                    deficit_classes.append((c, deficit))

        allocations: list[ClassContributionAllocation] = []
        total_deficit = sum(d for _, d in deficit_classes)

        # Distribuir o aporte proporcionalmente ao déficit
        assigned_amounts: dict[str, float] = {}
        if total_deficit > 0:
            for c, defic in deficit_classes:
                share = (defic / total_deficit) * amount
                assigned_amounts[c.asset_type] = round(share, 2)
        else:
            # Se não houver déficit específico, distribuir proporcionalmente às metas ou pesos atuais
            for c in analysis.classes:
                target_pct = c.allocation.target_weight_pct or c.allocation.current_weight_pct
                share = (target_pct / 100.0) * amount
                assigned_amounts[c.asset_type] = round(share, 2)

        # Ajuste de centavos no maior aporte
        allocated_sum = sum(assigned_amounts.values())
        diff = round(amount - allocated_sum, 2)
        if diff != 0 and assigned_amounts:
            max_key = max(assigned_amounts, key=lambda k: assigned_amounts[k])
            assigned_amounts[max_key] = round(assigned_amounts[max_key] + diff, 2)

        for c in analysis.classes:
            alloc_amt = assigned_amounts.get(c.asset_type, 0.0)
            proj_val = c.allocation.current_value + alloc_amt
            proj_pct = (proj_val / projected_total) * 100.0 if projected_total > 0 else 0.0

            if alloc_amt > 0:
                explanation = f"Recebe R$ {alloc_amt:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + f" para aproximar a fatia da meta ({proj_pct:.1f}%)."
            else:
                explanation = "Sem alocação adicional nesta simulação; classe já opera acima ou dentro da meta."

            allocations.append(
                ClassContributionAllocation(
                    asset_type=c.asset_type,
                    label=c.label,
                    current_value=c.allocation.current_value,
                    current_weight_pct=c.allocation.current_weight_pct,
                    target_weight_pct=c.allocation.target_weight_pct,
                    allocated_amount=alloc_amt,
                    projected_value=round(proj_val, 2),
                    projected_weight_pct=round(proj_pct, 2),
                    action_explanation=explanation,
                )
            )

        impact_summary = await self.explainer.explain_simulation(analysis, amount, allocations)
        elapsed = (time.perf_counter() - start_time) * 1000

        return ContributionSimulationResponse(
            portfolio_id=portfolio_id,
            contribution_amount=amount,
            current_total_value=round(current_total, 2),
            projected_total_value=round(projected_total, 2),
            suggested_allocations=allocations,
            overall_impact_summary=impact_summary,
            metadata=AiExplanationMetadata(
                provider=getattr(self.explainer, "provider_name", "sgi-audit-explainer-v1"),
                model=getattr(self.explainer, "model_name", "deterministic-rule-engine"),
                is_mock_or_deterministic=True,
                execution_time_ms=round(elapsed, 2),
            ),
        )

    async def answer_ai_question(
        self, portfolio_id: int, user_id: int, question: str
    ) -> AiQuestionResponse:
        start_time = time.perf_counter()
        analysis = await self.analysis_service.get_portfolio_analysis(portfolio_id, user_id)
        ans, referenced_metrics = await self.explainer.answer_question(analysis, question)
        elapsed = (time.perf_counter() - start_time) * 1000

        return AiQuestionResponse(
            portfolio_id=portfolio_id,
            question=question,
            answer=ans,
            key_metrics_referenced=referenced_metrics,
            metadata=AiExplanationMetadata(
                provider=getattr(self.explainer, "provider_name", "sgi-audit-explainer-v1"),
                model=getattr(self.explainer, "model_name", "deterministic-rule-engine"),
                is_mock_or_deterministic=True,
                execution_time_ms=round(elapsed, 2),
            ),
        )
