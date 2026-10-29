"""Serviço de correlação de ativos com a carteira e insights de IA (Issue #58).

Calcula a posição do investidor (PM, total investido, ganho de capital, proventos,
YoC, peso na carteira e peso na classe) e produz insights explicáveis sobre
concentração, rebalanceamento e papel estratégico do ativo na carteira.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.asset_portfolio_insight import (
    AIAssetInsight,
    AssetPortfolioInsightResponse,
    AssetPortfolioPositionInsight,
)
from app.services.asset_enrichment_service import asset_enrichment_service
from app.services.canonical_positions_service import get_canonical_portfolio_positions
from app.services.class_target_service import get_targets_map

logger = logging.getLogger(__name__)


class AssetPortfolioInsightService:
    """Orquestra a visão 360 do ativo correlacionado à carteira do usuário."""

    async def get_insight(
        self,
        db: AsyncSession,
        portfolio_id: int,
        user_id: int,
        ticker: str,
    ) -> AssetPortfolioInsightResponse:
        clean_ticker = ticker.strip().upper()

        # 1. Obter posições canônicas da carteira (já verifica permissão do usuário)
        groups = await get_canonical_portfolio_positions(db, portfolio_id, user_id)

        # 2. Calcular patrimônio total e localizar o ativo
        total_portfolio_value = 0.0
        target_group = None
        target_pos = None

        for group in groups:
            total_portfolio_value += float(group.get("total_value") or 0.0)
            for pos in group.get("positions", []):
                if str(pos.get("ticker", "")).strip().upper() == clean_ticker:
                    target_group = group
                    target_pos = pos

        # 3. Metas de classe
        targets_map = await get_targets_map(db, portfolio_id)

        # 4. Enriquecimento de mercado (Issue #130)
        asset_type = target_pos.get("asset_type") if target_pos else None
        enrichment = await asset_enrichment_service.get_asset_enrichment(
            clean_ticker, asset_type=asset_type, db=db
        )

        # 5. Construir dados de posição na carteira
        if target_pos and target_group:
            qty = float(target_pos.get("quantity") or 0.0)
            avg_price = float(target_pos.get("average_price") or 0.0)
            inv_value = float(target_pos.get("invested_value") or (qty * avg_price))
            cur_price = float(target_pos.get("current_price") or 0.0)
            cur_value = float(target_pos.get("current_value") or (qty * cur_price))
            proventos = float(target_pos.get("proventos") or 0.0)

            cap_gain_val = cur_value - inv_value
            cap_gain_pct = (cap_gain_val / inv_value * 100.0) if inv_value > 0 else 0.0

            tot_ret_val = cap_gain_val + proventos
            tot_ret_pct = (tot_ret_val / inv_value * 100.0) if inv_value > 0 else 0.0

            port_weight = (
                (cur_value / total_portfolio_value * 100.0)
                if total_portfolio_value > 0
                else 0.0
            )

            grp_total = float(target_group.get("total_value") or 0.0)
            class_weight = (cur_value / grp_total * 100.0) if grp_total > 0 else 0.0

            class_name = str(target_group.get("asset_type", ""))
            class_label = str(target_group.get("label", class_name))
            class_cur_alloc = (
                (grp_total / total_portfolio_value * 100.0)
                if total_portfolio_value > 0
                else 0.0
            )
            class_target = targets_map.get(class_name)

            yoc = (proventos / inv_value * 100.0) if inv_value > 0 else None

            pos_insight = AssetPortfolioPositionInsight(
                is_held=True,
                quantity=round(qty, 6),
                average_price=round(avg_price, 2),
                invested_value=round(inv_value, 2),
                current_price=round(cur_price, 2),
                current_value=round(cur_value, 2),
                capital_gain_value=round(cap_gain_val, 2),
                capital_gain_percent=round(cap_gain_pct, 2),
                dividends_received=round(proventos, 2),
                total_return_value=round(tot_ret_val, 2),
                total_return_percent=round(tot_ret_pct, 2),
                portfolio_weight_percent=round(port_weight, 2),
                class_weight_percent=round(class_weight, 2),
                class_name=class_name,
                class_label=class_label,
                class_current_allocation_percent=round(class_cur_alloc, 2),
                class_target_percent=round(class_target, 2) if class_target is not None else None,
                yield_on_cost_percent=round(yoc, 2) if yoc is not None else None,
            )
        else:
            pos_insight = AssetPortfolioPositionInsight(
                is_held=False,
            )

        # 6. Geração de Insights de IA & Determinísticos
        ai_insights = self._generate_ai_insights(clean_ticker, pos_insight, enrichment)

        return AssetPortfolioInsightResponse(
            ticker=clean_ticker,
            portfolio_id=portfolio_id,
            position=pos_insight,
            enrichment=enrichment,
            ai_insights=ai_insights,
        )

    def _generate_ai_insights(
        self,
        ticker: str,
        pos: AssetPortfolioPositionInsight,
        enrichment: dict[str, Any],
    ) -> AIAssetInsight:
        tipo = (pos.class_name or "").upper()
        crypto_data = enrichment.get("crypto_indicators")
        treasury_data = enrichment.get("treasury_indicators")
        intl_profile = enrichment.get("international_profile")
        fii_data = enrichment.get("fii_indicators")
        stock_data = enrichment.get("stock_fundamentals")

        # Concentração
        if not pos.is_held:
            concentration_level = "LOW"
            concentration_msg = (
                f"{ticker} não está presente na carteira atualmente. Sem risco de concentração."
            )
        elif "CRIPTO" in tipo or crypto_data:
            if pos.portfolio_weight_percent > 10.0:
                concentration_level = "HIGH"
                concentration_msg = (
                    f"Atenção: A exposição ao criptoativo {ticker} é de {pos.portfolio_weight_percent:.1f}%, "
                    f"superando o limite prudencial recomendado (5% a 10%) para ativos de alta volatilidade."
                )
            elif pos.portfolio_weight_percent >= 5.0:
                concentration_level = "WARNING"
                concentration_msg = (
                    f"{ticker} representa {pos.portfolio_weight_percent:.1f}% da carteira. Posição expressiva "
                    f"em criptoativo; monitore a volatilidade dos ciclos de mercado."
                )
            else:
                concentration_level = "BALANCED"
                concentration_msg = (
                    f"Posição equilibrada em criptoativo: {ticker} representa {pos.portfolio_weight_percent:.1f}% do portfólio."
                )
        elif "TESOURO" in tipo or "RENDA_FIXA" in tipo or treasury_data:
            concentration_level = "BALANCED"
            concentration_msg = (
                f"{ticker} compõe {pos.portfolio_weight_percent:.1f}% da carteira como âncora de segurança "
                f"e liquidez com risco soberano."
            )
        elif pos.portfolio_weight_percent > 15.0:
            concentration_level = "HIGH"
            concentration_msg = (
                f"Atenção: {ticker} representa {pos.portfolio_weight_percent:.1f}% de todo o patrimônio "
                f"da carteira, excedendo o teto prudencial sugerido de 15%. Risco de concentração elevado."
            )
        elif pos.portfolio_weight_percent >= 10.0:
            concentration_level = "WARNING"
            concentration_msg = (
                f"{ticker} representa {pos.portfolio_weight_percent:.1f}% da carteira. Posição expressiva, "
                f"recomenda-se ponderação antes de novos aportes para evitar sobreexposição."
            )
        else:
            concentration_level = "BALANCED"
            concentration_msg = (
                f"Posição equilibrada: {ticker} representa {pos.portfolio_weight_percent:.1f}% da carteira "
                f"e {pos.class_weight_percent:.1f}% da sua classe ({pos.class_label or 'Classe'})."
            )

        # Geração de Renda / YoC
        market_dy: Optional[float] = None
        if fii_data and fii_data.get("dividend_yield") is not None:
            market_dy = float(fii_data["dividend_yield"])
        elif stock_data and stock_data.get("dividend_yield") is not None:
            market_dy = float(stock_data["dividend_yield"])

        if "CRIPTO" in tipo or crypto_data:
            income_assessment = "Criptoativos não distribuem proventos regulares; seu retorno decorre primordialmente da valorização de capital."
        elif "TESOURO" in tipo or "RENDA_FIXA" in tipo or treasury_data:
            coupon_type = str(treasury_data.get("coupon_type", "") if treasury_data else "").lower()
            if "juros" in coupon_type:
                income_assessment = "Título com pagamento semestral de cupons de juros, propiciando fluxo de renda passiva intermediário."
            else:
                income_assessment = "Rendimentos acumulados e capitalizados automaticamente até o vencimento ou resgate antecipado."
        elif pos.is_held and pos.yield_on_cost_percent is not None and pos.dividends_received > 0:
            if market_dy is not None and pos.yield_on_cost_percent >= market_dy:
                income_assessment = (
                    f"Excelente geração de renda: seu Yield on Cost acumulado é de "
                    f"{pos.yield_on_cost_percent:.2f}%, superando o Dividend Yield de mercado atual "
                    f"({market_dy:.2f}%). Sua posição valorizou gerando retornos sobre o capital investido."
                )
            else:
                comp = f" frente ao DY de mercado de {market_dy:.2f}%" if market_dy is not None else ""
                income_assessment = (
                    f"Retorno em proventos: o ativo já retornou R$ {pos.dividends_received:,.2f} em proventos "
                    f"nesta carteira (Yield on Cost de {pos.yield_on_cost_percent:.2f}%{comp})."
                )
        else:
            if market_dy is not None and market_dy > 0:
                income_assessment = (
                    f"O ativo possui Dividend Yield de mercado atual de {market_dy:.2f}% a.a."
                )
            else:
                income_assessment = "Ativo com foco primordial em valorização patrimonial ou em fase inicial de histórico de proventos."

        # Rebalanceamento
        if pos.class_name and pos.class_target_percent is not None:
            diff = pos.class_current_allocation_percent - pos.class_target_percent
            if diff < -2.0:
                rebalancing_guidance = (
                    f"A classe {pos.class_label} está sub-alocada ({pos.class_current_allocation_percent:.1f}% "
                    f"vs meta de {pos.class_target_percent:.1f}%). Aportes em {ticker} contribuem "
                    f"para o rebalanceamento da carteira rumo ao objetivo."
                )
            elif diff > 2.0:
                rebalancing_guidance = (
                    f"A classe {pos.class_label} está sobre-alocada ({pos.class_current_allocation_percent:.1f}% "
                    f"vs meta de {pos.class_target_percent:.1f}%). Sugere-se direcionar novos aportes "
                    f"para outras classes deficitárias."
                )
            else:
                rebalancing_guidance = (
                    f"A classe {pos.class_label} está em conformidade com o alvo estratégico "
                    f"({pos.class_current_allocation_percent:.1f}% vs meta de {pos.class_target_percent:.1f}%)."
                )
        else:
            rebalancing_guidance = "Metas de alocação por classe ainda não definidas para esta carteira."

        # Papel Estratégico & Valuation Note
        valuation_note = ""
        if "CRIPTO" in tipo or crypto_data:
            rank_str = f" (Rank #{crypto_data.get('market_cap_rank')} global)" if crypto_data and crypto_data.get("market_cap_rank") else ""
            strategic_role = f"Reserva descentralizada e alta assimetria de valorização{rank_str}."
            if crypto_data and crypto_data.get("change_24h_pct") is not None:
                chg = float(crypto_data["change_24h_pct"])
                valuation_note = f" Variação nas últimas 24h: {chg:+.2f}%."
        elif "TESOURO" in tipo or "RENDA_FIXA" in tipo or treasury_data:
            indexer = treasury_data.get("indexer") if treasury_data else "Pós-fixado"
            if indexer == "IPCA":
                strategic_role = "Proteção contra a inflação com rentabilidade real garantida até o vencimento."
            elif indexer == "SELIC":
                strategic_role = "Preservação de capital, liquidez diária e remuneração atrelada à taxa básica de juros."
            else:
                strategic_role = "Previsibilidade de fluxo financeiro e rentabilidade prefixada pactuada."
            if treasury_data and treasury_data.get("buy_rate") is not None:
                rate = float(treasury_data["buy_rate"])
                mat = f" (vencimento {treasury_data.get('maturity_date')})" if treasury_data.get("maturity_date") else ""
                valuation_note = f" Taxa indicativa de compra: {rate:.2f}% a.a.{mat}."
        elif "FII" in tipo:
            seg_info = f" ({fii_data.get('segment') or fii_data.get('segment_type')})" if fii_data and (fii_data.get('segment') or fii_data.get('segment_type')) else ""
            strategic_role = f"Vetor de renda passiva mensal recorrente e diversificação imobiliária{seg_info}."
            if fii_data and fii_data.get("pvp") is not None:
                pvp_val = float(fii_data["pvp"])
                discount = (1.0 - pvp_val) * 100
                if discount > 2.0:
                    valuation_note = f" Negociando com desconto patrimonial de {discount:.1f}% (P/VP {pvp_val:.2f})."
                elif discount < -2.0:
                    valuation_note = f" Negociando com ágio patrimonial de {abs(discount):.1f}% (P/VP {pvp_val:.2f})."
                else:
                    valuation_note = f" Negociando em linha com o valor patrimonial (P/VP {pvp_val:.2f})."
        elif intl_profile or "STOCK" in tipo:
            industry_str = f" do setor de {intl_profile.get('industry')}" if intl_profile and intl_profile.get("industry") else ""
            strategic_role = f"Internacionalização do patrimônio e diversificação em moeda forte (USD){industry_str}."
            if stock_data and stock_data.get("pe") is not None:
                pe_val = float(stock_data["pe"])
                roe_str = f" e ROE de {float(stock_data['roe']):.1f}%" if stock_data.get("roe") is not None else ""
                rec_str = f" Consenso de Wall Street: {intl_profile.get('consensus')}." if intl_profile and intl_profile.get("consensus") else ""
                valuation_note = f" Apresenta múltiplo P/L de {pe_val:.1f}x{roe_str}.{rec_str}"
        elif "ACAO" in tipo or "BDR" in tipo:
            sector_info = f" do setor de {stock_data.get('sector')}" if stock_data and stock_data.get("sector") else ""
            if market_dy and market_dy >= 6.0:
                strategic_role = f"Empresa madura e geradora de caixa{sector_info} com distribuição relevante de dividendos/JCP."
            else:
                strategic_role = f"Ativo com potencial de crescimento dos lucros e valorização do capital{sector_info}."
            if stock_data and stock_data.get("pe") is not None:
                pe_val = float(stock_data["pe"])
                roe_str = f" e ROE de {float(stock_data['roe']):.1f}%" if stock_data.get("roe") is not None else ""
                valuation_note = f" Apresenta múltiplo P/L de {pe_val:.1f}x{roe_str}."
        else:
            strategic_role = "Ativo de diversificação patrimonial."

        # Resumo Explicável IA
        if pos.is_held:
            summary = (
                f"{ticker} cumpre o papel de {strategic_role.lower()} Com peso de {pos.portfolio_weight_percent:.1f}% "
                f"no portfólio, apresenta retorno total de {pos.total_return_percent:+.2f}% "
                f"(Ganho: {pos.capital_gain_percent:+.2f}%, Proventos: R$ {pos.dividends_received:,.2f})."
                f"{valuation_note} "
                f"{concentration_msg}"
            )
        else:
            summary = (
                f"{ticker} atua como {strategic_role.lower()}{valuation_note} Atualmente não compõe a custódia desta carteira."
            )

        return AIAssetInsight(
            concentration_level=concentration_level,
            concentration_message=concentration_msg,
            income_assessment=income_assessment,
            rebalancing_guidance=rebalancing_guidance,
            strategic_role=strategic_role,
            explainable_summary=summary,
        )


asset_portfolio_insight_service = AssetPortfolioInsightService()
