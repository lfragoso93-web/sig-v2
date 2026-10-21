from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import Portfolio
from app.models.portfolio_class_target import PortfolioClassTarget
from app.schemas.portfolio_analysis import (
    ClassAllocationAnalysis,
    ClassAnalysisDetail,
    ClassConcentrationAnalysis,
    ClassFixedIncomeAnalysis,
    ClassIncomeAnalysis,
    ConcentrationRiskLevel,
    PortfolioConsolidatedAnalysisResponse,
    RebalanceAction,
    TopAssetConcentration,
)
from app.schemas.portfolio_positions import PositionGroupResponse, PositionItemResponse
from app.services.canonical_positions_service import get_canonical_portfolio_positions


def _asset_type_from_group(group: PositionGroupResponse) -> str:
    if group.positions:
        return group.positions[0].asset_type
    norm = group.label.upper()
    if "AÇÕES" in norm or "ACAO" in norm:
        return "ACAO"
    if "FII" in norm:
        return "FII"
    if "TESOURO" in norm:
        return "TESOURO_DIRETO"
    if "RENDA FIXA" in norm:
        return "RENDA_FIXA"
    if "CRIPTO" in norm:
        return "CRIPTO"
    if "STOCK" in norm:
        return "STOCK"
    if "BDR" in norm:
        return "BDR"
    if "ETF" in norm and "INT" in norm:
        return "ETF_INTERNACIONAL"
    if "ETF" in norm:
        return "ETF_NACIONAL"
    return "OUTROS"


def _safe_float(val: Any) -> float:
    if val is None:
        return 0.0
    try:
        f = float(val)
        return f if f == f else 0.0
    except (ValueError, TypeError):
        return 0.0


def _compute_class_allocation(
    current_value: float,
    total_portfolio_value: float,
    target_pct: float | None,
) -> ClassAllocationAnalysis:
    current_weight = round(current_value / total_portfolio_value * 100.0, 2) if total_portfolio_value > 0 else 0.0

    if target_pct is not None and target_pct > 0:
        target_value = round(total_portfolio_value * (target_pct / 100.0), 2)
        gap_weight = round(current_weight - target_pct, 2)
        gap_val = round(target_value - current_value, 2)

        if gap_weight < -1.0:
            action = RebalanceAction.BUY
            action_label = f"Aporte sugerido de R$ {abs(gap_val):,.2f} para convergir à meta de {target_pct:.1f}%"
        elif gap_weight > 1.0:
            action = RebalanceAction.REDUCE
            action_label = f"Excesso de R$ {abs(gap_val):,.2f} ({abs(gap_weight):.1f}% acima da meta)"
        else:
            action = RebalanceAction.HOLD
            action_label = f"Alinhado à meta ({current_weight:.1f}% vs meta {target_pct:.1f}%)"
    else:
        target_value = None
        gap_weight = None
        gap_val = None
        action = RebalanceAction.HOLD
        action_label = "Sem meta de alocação definida para a classe"

    return ClassAllocationAnalysis(
        current_value=current_value,
        current_weight_pct=current_weight,
        target_weight_pct=target_pct,
        target_value=target_value,
        gap_weight_pct=gap_weight,
        gap_value=gap_val,
        rebalance_action=action,
        suggested_action_label=action_label,
    )


def _compute_class_concentration(
    positions: list[PositionItemResponse],
    class_total_value: float,
    total_portfolio_value: float,
) -> ClassConcentrationAnalysis:
    asset_count = len(positions)
    if not positions or class_total_value <= 0:
        return ClassConcentrationAnalysis(
            asset_count=asset_count,
            top_asset=None,
            hhi_score=None,
            risk_level=ConcentrationRiskLevel.LOW,
            risk_label="Baixo",
            status_message="Classe sem posições ativas.",
        )

    # Ordenar por valor decrescente
    sorted_pos = sorted(
        positions,
        key=lambda p: _safe_float(p.current_value if p.current_value is not None else p.invested_value),
        reverse=True,
    )
    top_pos = sorted_pos[0]
    top_val = _safe_float(top_pos.current_value if top_pos.current_value is not None else top_pos.invested_value)
    top_in_class_pct = round(top_val / class_total_value * 100.0, 2) if class_total_value > 0 else 0.0
    top_in_port_pct = round(top_val / total_portfolio_value * 100.0, 2) if total_portfolio_value > 0 else 0.0

    top_asset = TopAssetConcentration(
        ticker=top_pos.ticker,
        name=top_pos.asset_label or top_pos.ticker,
        current_value=top_val,
        weight_in_class_pct=top_in_class_pct,
        weight_in_portfolio_pct=top_in_port_pct,
    )

    # Herfindahl-Hirschman Index (HHI)
    hhi = sum((_safe_float(p.current_value or p.invested_value) / class_total_value * 100.0) ** 2 for p in sorted_pos)
    hhi_score = round(hhi, 1)

    # Nível de Risco
    if top_in_port_pct > 25.0 or (asset_count > 1 and top_in_class_pct > 65.0):
        risk = ConcentrationRiskLevel.CRITICAL
        risk_label = "Crítico"
        msg = f"Alta dependência de {top_pos.ticker} ({top_in_class_pct:.1f}% da classe, {top_in_port_pct:.1f}% da carteira)."
    elif top_in_port_pct > 15.0 or (asset_count > 1 and top_in_class_pct > 40.0):
        risk = ConcentrationRiskLevel.WARNING
        risk_label = "Atenção"
        msg = f"{top_pos.ticker} representa {top_in_class_pct:.1f}% do patrimônio desta classe."
    elif top_in_class_pct <= 25.0 or (asset_count == 1 and top_in_port_pct < 5.0):
        risk = ConcentrationRiskLevel.LOW
        risk_label = "Baixo"
        msg = f"Classe bem distribuída entre {asset_count} ativos (HHI {hhi_score})."
    else:
        risk = ConcentrationRiskLevel.BALANCED
        risk_label = "Equilibrado"
        msg = f"Concentração moderada em {top_pos.ticker} ({top_in_class_pct:.1f}% da classe)."

    return ClassConcentrationAnalysis(
        asset_count=asset_count,
        top_asset=top_asset,
        hhi_score=hhi_score,
        risk_level=risk,
        risk_label=risk_label,
        status_message=msg,
    )


def _compute_class_income(
    positions: list[PositionItemResponse],
    asset_type: str,
    class_total_value: float,
) -> ClassIncomeAnalysis:
    is_applicable = asset_type in {"ACAO", "ACAO_NACIONAL", "FII", "STOCK", "BDR"}
    if not is_applicable:
        return ClassIncomeAnalysis(
            is_applicable=False,
            total_proventos=0.0,
            weighted_dy_pct=None,
            top_income_asset=None,
            status_label="Não aplicável para esta classe",
        )

    total_prov = sum(_safe_float(p.proventos) for p in positions)
    top_income = None
    if positions:
        sorted_by_prov = sorted(positions, key=lambda p: _safe_float(p.proventos), reverse=True)
        if _safe_float(sorted_by_prov[0].proventos) > 0:
            top_income = sorted_by_prov[0].ticker

    yield_pct = round(total_prov / class_total_value * 100.0, 2) if class_total_value > 0 else 0.0

    return ClassIncomeAnalysis(
        is_applicable=True,
        total_proventos=round(total_prov, 2),
        weighted_dy_pct=yield_pct if total_prov > 0 else None,
        top_income_asset=top_income,
        status_label=f"R$ {total_prov:,.2f} recebidos" if total_prov > 0 else "Sem proventos no período",
    )


def _compute_class_fixed_income(
    positions: list[PositionItemResponse],
    asset_type: str,
    class_total_value: float,
) -> ClassFixedIncomeAnalysis:
    is_applicable = asset_type in {"TESOURO_DIRETO", "RENDA_FIXA"}
    if not is_applicable or not positions or class_total_value <= 0:
        return ClassFixedIncomeAnalysis(
            is_applicable=is_applicable,
            cdi_allocation_pct=None,
            ipca_allocation_pct=None,
            pre_allocation_pct=None,
            maturing_next_12m_value=None,
            maturing_next_12m_pct=None,
        )

    cdi_val = 0.0
    ipca_val = 0.0
    pre_val = 0.0
    maturing_12m = 0.0
    today = datetime.date.today()
    limit_12m = today + datetime.timedelta(days=365)

    for p in positions:
        val = _safe_float(p.current_value if p.current_value is not None else p.invested_value)
        indexer = (p.indexer or "").upper()
        if "CDI" in indexer or "DI" in indexer or "SELIC" in indexer:
            cdi_val += val
        elif "IPCA" in indexer or "IGP" in indexer or "INFLA" in indexer:
            ipca_val += val
        elif "PRE" in indexer:
            pre_val += val
        else:
            # Heurística pelo ticker/label
            t_upper = p.ticker.upper()
            if "SELIC" in t_upper:
                cdi_val += val
            elif "IPCA" in t_upper:
                ipca_val += val
            elif "PREFIXADO" in t_upper:
                pre_val += val
            else:
                cdi_val += val

        if p.maturity_date:
            try:
                m_date = datetime.date.fromisoformat(str(p.maturity_date)[:10])
                if today <= m_date <= limit_12m:
                    maturing_12m += val
            except (ValueError, TypeError):
                pass

    return ClassFixedIncomeAnalysis(
        is_applicable=True,
        cdi_allocation_pct=round(cdi_val / class_total_value * 100.0, 1),
        ipca_allocation_pct=round(ipca_val / class_total_value * 100.0, 1),
        pre_allocation_pct=round(pre_val / class_total_value * 100.0, 1),
        maturing_next_12m_value=round(maturing_12m, 2),
        maturing_next_12m_pct=round(maturing_12m / class_total_value * 100.0, 1) if class_total_value > 0 else 0.0,
    )


def _compute_class_health_score(
    allocation: ClassAllocationAnalysis,
    concentration: ClassConcentrationAnalysis,
    income: ClassIncomeAnalysis,
    fixed_income: ClassFixedIncomeAnalysis,
) -> int:
    score = 0

    # 1. Alocação perante a meta (0 a 40 pts)
    if allocation.target_weight_pct is not None:
        gap = abs(allocation.gap_weight_pct or 0.0)
        if gap <= 1.5:
            score += 40
        elif gap <= 4.0:
            score += 30
        elif gap <= 8.0:
            score += 15
        else:
            score += 5
    else:
        score += 25  # Neutro quando usuário não definiu meta

    # 2. Concentração (0 a 40 pts)
    if concentration.risk_level == ConcentrationRiskLevel.LOW:
        score += 40
    elif concentration.risk_level == ConcentrationRiskLevel.BALANCED:
        score += 30
    elif concentration.risk_level == ConcentrationRiskLevel.WARNING:
        score += 15
    else:
        score += 5

    # 3. Diversificação & Renda (0 a 20 pts)
    if concentration.asset_count >= 5:
        score += 20
    elif concentration.asset_count >= 2:
        score += 15
    elif concentration.asset_count == 1:
        score += 10
    else:
        score += 0

    return min(100, max(0, score))


class PortfolioAnalysisService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_portfolio_analysis(
        self,
        portfolio_id: int,
        user_id: int,
    ) -> PortfolioConsolidatedAnalysisResponse:
        # 1. Carregar portfólio
        portfolio = await self.db.get(Portfolio, portfolio_id)
        if not portfolio or portfolio.user_id != user_id:
            raise ValueError(f"Portfólio {portfolio_id} não encontrado ou acesso não autorizado.")

        # 2. Posições canônicas já consolidadas (sem duplicar valuation)
        groups_raw = await get_canonical_portfolio_positions(self.db, portfolio_id, user_id)
        groups: list[PositionGroupResponse] = [
            g if isinstance(g, PositionGroupResponse) else PositionGroupResponse.model_validate(g)
            for g in groups_raw
        ]

        # 3. Metas canônicas da carteira
        targets_stmt = select(PortfolioClassTarget).where(PortfolioClassTarget.portfolio_id == portfolio_id)
        target_records = (await self.db.execute(targets_stmt)).scalars().all()
        targets_map: dict[str, float] = {t.asset_type.upper(): float(t.target_pct) for t in target_records}

        # 4. Calcular patrimônio total da carteira
        total_portfolio_value = 0.0
        for g in groups:
            val = _safe_float(getattr(g, "total_value", None) if getattr(g, "total_value", None) is not None else getattr(g, "total_invested", 0.0))
            total_portfolio_value += val

        total_portfolio_value = round(total_portfolio_value, 2)

        # 5. Processar cada classe
        class_details: list[ClassAnalysisDetail] = []
        priority_rebalance_classes: list[str] = []
        max_divergence_class: str | None = None
        max_divergence_val = -1.0

        total_weighted_score = 0.0

        for group in groups:
            asset_type = _asset_type_from_group(group)
            class_val = round(_safe_float(getattr(group, "total_value", None) if getattr(group, "total_value", None) is not None else getattr(group, "total_invested", 0.0)), 2)
            target_pct = targets_map.get(asset_type.upper(), getattr(group, "target_pct", None))

            allocation = _compute_class_allocation(class_val, total_portfolio_value, target_pct)
            concentration = _compute_class_concentration(group.positions, class_val, total_portfolio_value)
            income = _compute_class_income(group.positions, asset_type, class_val)
            fixed_income = _compute_class_fixed_income(group.positions, asset_type, class_val)

            health_score = _compute_class_health_score(allocation, concentration, income, fixed_income)

            findings: list[str] = []
            if allocation.rebalance_action == RebalanceAction.BUY:
                findings.append(allocation.suggested_action_label)
                priority_rebalance_classes.append(group.label)
            elif allocation.rebalance_action == RebalanceAction.REDUCE:
                findings.append(allocation.suggested_action_label)

            if concentration.risk_level in {ConcentrationRiskLevel.WARNING, ConcentrationRiskLevel.CRITICAL}:
                findings.append(concentration.status_message)

            if income.is_applicable and income.total_proventos > 0:
                findings.append(f"Geração de renda: R$ {income.total_proventos:,.2f} no histórico.")

            if fixed_income.is_applicable and fixed_income.cdi_allocation_pct is not None:
                findings.append(f"Distribuição RF: CDI/Selic {fixed_income.cdi_allocation_pct}% | IPCA {fixed_income.ipca_allocation_pct}% | Pré {fixed_income.pre_allocation_pct}%.")

            if allocation.gap_weight_pct is not None and abs(allocation.gap_weight_pct) > max_divergence_val:
                max_divergence_val = abs(allocation.gap_weight_pct)
                max_divergence_class = group.label

            # Acumular score ponderado pelo peso da classe
            weight = (class_val / total_portfolio_value) if total_portfolio_value > 0 else 0.0
            total_weighted_score += health_score * weight

            class_details.append(
                ClassAnalysisDetail(
                    asset_type=asset_type,
                    label=group.label,
                    health_score=health_score,
                    allocation=allocation,
                    concentration=concentration,
                    income=income,
                    fixed_income=fixed_income,
                    key_findings=findings,
                )
            )

        overall_score = round(total_weighted_score) if class_details and total_portfolio_value > 0 else 70

        return PortfolioConsolidatedAnalysisResponse(
            portfolio_id=portfolio_id,
            portfolio_name=portfolio.name,
            reference_date=datetime.date.today().isoformat(),
            total_value=total_portfolio_value,
            overall_health_score=min(100, max(0, overall_score)),
            max_divergence_class=max_divergence_class,
            classes_analyzed_count=len(class_details),
            rebalance_priority_classes=priority_rebalance_classes,
            classes=class_details,
            provenance={
                "valuation": "canonical intraday/last close position valuation via get_canonical_portfolio_positions",
                "targets": "canonical portfolio_class_targets",
                "concentration": "Herfindahl-Hirschman Index and Top-1 concentration share",
                "income": "canonical dividends ledger on open positions",
                "fixed_income": "canonical fixed income contracts and asset metadata",
            },
        )
