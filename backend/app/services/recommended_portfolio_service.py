from __future__ import annotations

import logging
from typing import Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_price import AssetPrice
from app.schemas.recommended_portfolio import (
    RecommendedPortfolio,
    RecommendedPortfolioSimulationRequest,
    RecommendedPortfolioSimulationResponse,
    SimulatedAssetAllocation,
    SimulatedClassAllocation,
)

logger = logging.getLogger(__name__)

# Base templates das carteiras recomendadas
RAW_PORTFOLIOS: dict[str, dict] = {
    "patrimonio": {
        "id": "patrimonio",
        "title": "Aumento e Preservação de Patrimônio",
        "subtitle": "Crescimento sustentável com foco em baixa volatilidade e valor real",
        "strategy": "patrimonio",
        "thesis": (
            "Estratégia focada na acumulação constante e blindagem de patrimônio no longo prazo. "
            "Combina títulos públicos atrelados à inflação (IPCA+), reserva segura pós-fixada (CDI), "
            "empresas consolidadas de alta geração de caixa (Blue Chips) e Fundos Imobiliários logísticos "
            "com contratos atípicos de padrão institucional."
        ),
        "risk_profile": "Moderado / Defensivo",
        "expected_annual_return": "IPCA + 6,5% a 8,0% a.a.",
        "expected_dividend_yield": "5,0% a 6,5% a.a.",
        "suggested_time_horizon": "Mínimo 5 anos",
        "diversification_score": 93,
        "classes": [
            {
                "asset_type": "RENDA_FIXA",
                "label": "Renda Fixa",
                "target_weight_pct": 30.0,
                "description": "Liquidez e previsibilidade para estabilização de volatilidade e reserva.",
                "assets": [
                    {
                        "ticker": "CDB-DI-LIQUIDEZ",
                        "name": "CDB 100% CDI Liquidez Diária",
                        "asset_type": "RENDA_FIXA",
                        "current_price": 1000.0,
                        "target_weight_pct": 18.0,
                        "expected_yield_pct": 10.75,
                        "risk_level": "low",
                        "reason": "Reserva de liquidez imediata com cobertura do FGC e rendimento diário pós-fixado.",
                    },
                    {
                        "ticker": "LCI-DI-90D",
                        "name": "LCI DI Isenta 95% CDI",
                        "asset_type": "RENDA_FIXA",
                        "current_price": 1000.0,
                        "target_weight_pct": 12.0,
                        "expected_yield_pct": 10.20,
                        "risk_level": "low",
                        "reason": "Isenção total de Imposto de Renda para pessoa física, maximizando rentabilidade líquida.",
                    },
                ],
            },
            {
                "asset_type": "TESOURO_DIRETO",
                "label": "Tesouro Direto",
                "target_weight_pct": 25.0,
                "description": "Títulos soberanos protegendo o capital contra a inflação e assegurando juro real.",
                "assets": [
                    {
                        "ticker": "Tesouro IPCA+ 2029",
                        "name": "Tesouro IPCA+ 2029 (NTN-B Principal)",
                        "asset_type": "TESOURO_DIRETO",
                        "current_price": 3200.0,
                        "target_weight_pct": 15.0,
                        "expected_yield_pct": 6.50,
                        "risk_level": "low",
                        "reason": "Proteção integral contra corrosão inflacionária com taxa real contratada soberana.",
                    },
                    {
                        "ticker": "Tesouro Selic 2029",
                        "name": "Tesouro Selic 2029 (LFT)",
                        "asset_type": "TESOURO_DIRETO",
                        "current_price": 15000.0,
                        "target_weight_pct": 10.0,
                        "expected_yield_pct": 10.75,
                        "risk_level": "low",
                        "reason": "Ativo de menor risco de crédito da economia brasileira e sem risco de marcação a mercado no resgate.",
                    },
                ],
            },
            {
                "asset_type": "ACAO",
                "label": "Ações Nacionais",
                "target_weight_pct": 25.0,
                "description": "Participação em grandes corporações com vantagens competitivas duráveis.",
                "assets": [
                    {
                        "ticker": "ITUB4",
                        "name": "Itaú Unibanco PN",
                        "asset_type": "ACAO",
                        "current_price": 35.50,
                        "target_weight_pct": 10.0,
                        "expected_yield_pct": 6.80,
                        "risk_level": "moderate",
                        "reason": "Maior banco privado da América Latina, ROE superior a 20% e histórico comprovado de resiliência e solidez.",
                    },
                    {
                        "ticker": "VALE3",
                        "name": "Vale ON",
                        "asset_type": "ACAO",
                        "current_price": 60.50,
                        "target_weight_pct": 8.0,
                        "expected_yield_pct": 8.20,
                        "risk_level": "moderate",
                        "reason": "Líder mundial em minério de ferro com custo caixa C1 ultracompetitivo e forte retorno ao acionista.",
                    },
                    {
                        "ticker": "EGIE3",
                        "name": "Engie Brasil ON",
                        "asset_type": "ACAO",
                        "current_price": 42.00,
                        "target_weight_pct": 7.0,
                        "expected_yield_pct": 7.10,
                        "risk_level": "low",
                        "reason": "Geração e transmissão de energia com receitas previsíveis e contratos de longo prazo corrigidos por índices inflacionários.",
                    },
                ],
            },
            {
                "asset_type": "FII",
                "label": "Fundos Imobiliários",
                "target_weight_pct": 15.0,
                "description": "Ativos imobiliários de alta qualidade com proventos periódicos e lastro físico.",
                "assets": [
                    {
                        "ticker": "HGLG11",
                        "name": "CSHG Logística FII",
                        "asset_type": "FII",
                        "current_price": 162.00,
                        "target_weight_pct": 8.0,
                        "expected_yield_pct": 8.40,
                        "risk_level": "low",
                        "reason": "Portfólio maduro de galpões logísticos de alto padrão construtivo próximos aos maiores polos consumidores.",
                    },
                    {
                        "ticker": "KNIP11",
                        "name": "Kinea Índices de Preços FII",
                        "asset_type": "FII",
                        "current_price": 94.00,
                        "target_weight_pct": 7.0,
                        "expected_yield_pct": 9.80,
                        "risk_level": "moderate",
                        "reason": "Fundo de papel devedor com CRIs indexados ao IPCA e garantias de primeiro escalão com alta liquidez.",
                    },
                ],
            },
            {
                "asset_type": "CRIPTO",
                "label": "Criptoativos",
                "target_weight_pct": 5.0,
                "description": "Reserva descentralizada e diversificação assimétrica de capital.",
                "assets": [
                    {
                        "ticker": "BTC",
                        "name": "Bitcoin",
                        "asset_type": "CRIPTO",
                        "current_price": 420000.0,
                        "target_weight_pct": 5.0,
                        "expected_yield_pct": 0.0,
                        "risk_level": "high",
                        "reason": "Reserva de valor digital escassa e descentralizada com política monetária programada e imutável.",
                    },
                ],
            },
        ],
    },
    "proventos": {
        "id": "proventos",
        "title": "Renda Passiva e Fluxo de Proventos",
        "subtitle": "Maximização de fluxo de caixa mensal e dividend yield sustentável",
        "strategy": "proventos",
        "thesis": (
            "Construída para gerar um fluxo mensal consistente, crescente e preferencialmente isento de impostos. "
            "Combina Fundos Imobiliários com foco em renda recorrente, empresas líderes com políticas agressivas "
            "e perenes de distribuição de dividendos e instrumentos de renda fixa isentos de tributação na fonte."
        ),
        "risk_profile": "Moderado",
        "expected_annual_return": "10,5% a 13,0% a.a. total",
        "expected_dividend_yield": "8,8% a 11,5% a.a.",
        "suggested_time_horizon": "Mínimo 3 anos",
        "diversification_score": 91,
        "classes": [
            {
                "asset_type": "FII",
                "label": "Fundos Imobiliários",
                "target_weight_pct": 40.0,
                "description": "Coluna dorsal de proventos mensais isentos de IR para pessoa física.",
                "assets": [
                    {
                        "ticker": "MXRF11",
                        "name": "Maxi Renda FII",
                        "asset_type": "FII",
                        "current_price": 10.40,
                        "target_weight_pct": 12.0,
                        "expected_yield_pct": 11.80,
                        "risk_level": "moderate",
                        "reason": "Maior liquidez da indústria brasileira de FIIs com carteira diversificada de recebíveis imobiliários.",
                    },
                    {
                        "ticker": "HGLG11",
                        "name": "CSHG Logística FII",
                        "asset_type": "FII",
                        "current_price": 162.00,
                        "target_weight_pct": 10.0,
                        "expected_yield_pct": 8.40,
                        "risk_level": "low",
                        "reason": "Estabilidade de proventos ancorada em locatários multinacionais e contratos de longo prazo.",
                    },
                    {
                        "ticker": "XPML11",
                        "name": "XP Malls FII",
                        "asset_type": "FII",
                        "current_price": 112.00,
                        "target_weight_pct": 10.0,
                        "expected_yield_pct": 9.20,
                        "risk_level": "moderate",
                        "reason": "Participação nos principais shoppings centers do país, com fluxo de aluguel vinculado ao faturamento dos lojistas.",
                    },
                    {
                        "ticker": "KNCR11",
                        "name": "Kinea Rendimentos Imobiliários FII",
                        "asset_type": "FII",
                        "current_price": 102.50,
                        "target_weight_pct": 8.0,
                        "expected_yield_pct": 11.20,
                        "risk_level": "low",
                        "reason": "Fundo de CRI indexado majoritariamente ao CDI, pagando proventos mensais elevados com baixo risco de crédito.",
                    },
                ],
            },
            {
                "asset_type": "ACAO",
                "label": "Ações Pagadoras de Dividendos",
                "target_weight_pct": 30.0,
                "description": "Companhias com modelo de negócios gerador de caixa e payout robusto.",
                "assets": [
                    {
                        "ticker": "BBAS3",
                        "name": "Banco do Brasil ON",
                        "asset_type": "ACAO",
                        "current_price": 28.50,
                        "target_weight_pct": 10.0,
                        "expected_yield_pct": 9.80,
                        "risk_level": "moderate",
                        "reason": "Avaliação descontada por múltiplos, carteira agro defensiva e histórico consistente de distribuição de proventos.",
                    },
                    {
                        "ticker": "TAEE11",
                        "name": "Taesa Unit",
                        "asset_type": "ACAO",
                        "current_price": 36.00,
                        "target_weight_pct": 10.0,
                        "expected_yield_pct": 9.50,
                        "risk_level": "low",
                        "reason": "Transmissora pura de energia com receitas anuais permitidas (RAP) reajustadas por IGPM/IPCA sem risco de demanda.",
                    },
                    {
                        "ticker": "PETR4",
                        "name": "Petrobras PN",
                        "asset_type": "ACAO",
                        "current_price": 37.00,
                        "target_weight_pct": 5.0,
                        "expected_yield_pct": 13.50,
                        "risk_level": "high",
                        "reason": "Fluxo de caixa livre robusto no pré-sal com política de dividendos gerando yield extraordinário.",
                    },
                    {
                        "ticker": "VIVT3",
                        "name": "Telefônica Brasil ON (Vivo)",
                        "asset_type": "ACAO",
                        "current_price": 54.00,
                        "target_weight_pct": 5.0,
                        "expected_yield_pct": 7.80,
                        "risk_level": "low",
                        "reason": "Geração estável de caixa no setor de telecomunicações com forte distribuição via Juros sobre Capital Próprio e dividendos.",
                    },
                ],
            },
            {
                "asset_type": "RENDA_FIXA",
                "label": "Renda Fixa Isenta",
                "target_weight_pct": 15.0,
                "description": "CRI, CRA, LCI e LCA isentos de imposto de renda.",
                "assets": [
                    {
                        "ticker": "LCA-AGRO-DI",
                        "name": "LCA Agronegócio 94% CDI",
                        "asset_type": "RENDA_FIXA",
                        "current_price": 1000.0,
                        "target_weight_pct": 10.0,
                        "expected_yield_pct": 10.10,
                        "risk_level": "low",
                        "reason": "Título isento garantido pelo FGC com remuneração líquida superior aos títulos convencionais tributados.",
                    },
                    {
                        "ticker": "CRI-SENIOR-IPCA",
                        "name": "CRI Sênior IPCA + 6,8% Isento",
                        "asset_type": "RENDA_FIXA",
                        "current_price": 1000.0,
                        "target_weight_pct": 5.0,
                        "expected_yield_pct": 10.80,
                        "risk_level": "moderate",
                        "reason": "Fluxo periódico de amortização e juros isentos de IR com garantia real de imóveis.",
                    },
                ],
            },
            {
                "asset_type": "TESOURO_DIRETO",
                "label": "Tesouro Direto",
                "target_weight_pct": 10.0,
                "description": "Títulos do Tesouro Nacional estruturados para aposentadoria e renda.",
                "assets": [
                    {
                        "ticker": "Tesouro Renda+ 2030",
                        "name": "Tesouro RendA+ 2030 (Aposentadoria)",
                        "asset_type": "TESOURO_DIRETO",
                        "current_price": 1600.0,
                        "target_weight_pct": 10.0,
                        "expected_yield_pct": 6.40,
                        "risk_level": "low",
                        "reason": "Título desenhado para pagar 240 parcelas mensais de renda corrigidas pela inflação a partir de 2030.",
                    },
                ],
            },
            {
                "asset_type": "ETF_INTERNACIONAL",
                "label": "Internacional em Dividendos",
                "target_weight_pct": 5.0,
                "description": "Diversificação cambial com foco em empresas aristocratas de proventos.",
                "assets": [
                    {
                        "ticker": "VYM",
                        "name": "Vanguard High Dividend Yield ETF",
                        "asset_type": "ETF_INTERNACIONAL",
                        "current_price": 680.0,
                        "target_weight_pct": 5.0,
                        "expected_yield_pct": 3.40,
                        "risk_level": "moderate",
                        "reason": "Exposição em moeda forte (USD) às 400 maiores pagadoras de dividendos dos Estados Unidos.",
                    },
                ],
            },
        ],
    },
    "performance": {
        "id": "performance",
        "title": "Performance, Tecnologia e Crescimento",
        "subtitle": "Maximização de ganho de capital composto com inovação e expansão secular",
        "strategy": "performance",
        "thesis": (
            "Estruturada para investidores que buscam retorno total acima dos índices tradicionais através "
            "de teses de crescimento secular: inteligência artificial, computação em nuvem, empresas com alto ROIC, "
            "ativos digitais com oferta programada e papéis de média/pequena capitalização com alto potencial."
        ),
        "risk_profile": "Arrojado",
        "expected_annual_return": "15,0% a 22,0%+ a.a.",
        "expected_dividend_yield": "2,0% a 3,5% a.a.",
        "suggested_time_horizon": "Mínimo 5 a 10 anos",
        "diversification_score": 89,
        "classes": [
            {
                "asset_type": "ACAO",
                "label": "Ações de Crescimento",
                "target_weight_pct": 35.0,
                "description": "Empresas com vantagens competitivas ampliadas, alto ROIC e reinvestimento acelerado.",
                "assets": [
                    {
                        "ticker": "WEGE3",
                        "name": "WEG ON",
                        "asset_type": "ACAO",
                        "current_price": 54.00,
                        "target_weight_pct": 14.0,
                        "expected_yield_pct": 2.20,
                        "risk_level": "moderate",
                        "reason": "Líder global em eficiência energética, motores industriais e transição elétrica com ROIC superior a 30%.",
                    },
                    {
                        "ticker": "PRIO3",
                        "name": "PRIO ON",
                        "asset_type": "ACAO",
                        "current_price": 44.00,
                        "target_weight_pct": 11.0,
                        "expected_yield_pct": 1.50,
                        "risk_level": "high",
                        "reason": "Maior produtora independente de petróleo e gás com excelente histórico de revitalização de campos maduros.",
                    },
                    {
                        "ticker": "SMAL11",
                        "name": "iShares Small Cap ETF",
                        "asset_type": "ACAO",
                        "current_price": 105.00,
                        "target_weight_pct": 10.0,
                        "expected_yield_pct": 2.80,
                        "risk_level": "high",
                        "reason": "Cesta representativa das companhias com maior potencial de multiplicação no mercado de capitais brasileiro.",
                    },
                ],
            },
            {
                "asset_type": "STOCK",
                "label": "Stocks & Big Tech Global",
                "target_weight_pct": 25.0,
                "description": "Líderes mundiais em infraestrutura de IA, semicondutores e plataformas digitais.",
                "assets": [
                    {
                        "ticker": "NVDA",
                        "name": "NVIDIA Corporation",
                        "asset_type": "STOCK",
                        "current_price": 750.0,
                        "target_weight_pct": 10.0,
                        "expected_yield_pct": 0.50,
                        "risk_level": "high",
                        "reason": "Monopólio prático em GPUs aceleradoras e plataformas CUDA indispensáveis para o avanço da IA generativa.",
                    },
                    {
                        "ticker": "AAPL",
                        "name": "Apple Inc",
                        "asset_type": "STOCK",
                        "current_price": 1250.0,
                        "target_weight_pct": 8.0,
                        "expected_yield_pct": 0.80,
                        "risk_level": "moderate",
                        "reason": "Ecossistema global com mais de 2 bilhões de aparelhos ativos e geração massiva de fluxo de caixa livre.",
                    },
                    {
                        "ticker": "QQQ",
                        "name": "Invesco QQQ (Nasdaq 100)",
                        "asset_type": "ETF_INTERNACIONAL",
                        "current_price": 2600.0,
                        "target_weight_pct": 7.0,
                        "expected_yield_pct": 0.70,
                        "risk_level": "moderate",
                        "reason": "Exposição direta às 100 maiores companhias não financeiras da Nasdaq com liderança em inovação tecnológica.",
                    },
                ],
            },
            {
                "asset_type": "CRIPTO",
                "label": "Criptoativos & Web3",
                "target_weight_pct": 15.0,
                "description": "Ativos digitais com alto potencial de valorização e inovação tecnológica.",
                "assets": [
                    {
                        "ticker": "BTC",
                        "name": "Bitcoin",
                        "asset_type": "CRIPTO",
                        "current_price": 420000.0,
                        "target_weight_pct": 10.0,
                        "expected_yield_pct": 0.0,
                        "risk_level": "high",
                        "reason": "Reserva de valor descentralizada e instrumento de hedge contra a expansão monetária global.",
                    },
                    {
                        "ticker": "ETH",
                        "name": "Ethereum",
                        "asset_type": "CRIPTO",
                        "current_price": 19500.0,
                        "target_weight_pct": 5.0,
                        "expected_yield_pct": 3.20,
                        "risk_level": "high",
                        "reason": "Principal ecossistema de finanças descentralizadas (DeFi), tokenização de ativos do mundo real e smart contracts.",
                    },
                ],
            },
            {
                "asset_type": "FII",
                "label": "FIIs de Ganho de Capital",
                "target_weight_pct": 15.0,
                "description": "Shoppings e logística com potencial de valorização de cotas e reavaliação patrimonial.",
                "assets": [
                    {
                        "ticker": "XPML11",
                        "name": "XP Malls FII",
                        "asset_type": "FII",
                        "current_price": 112.00,
                        "target_weight_pct": 8.0,
                        "expected_yield_pct": 9.20,
                        "risk_level": "moderate",
                        "reason": "Shoppings dominantes com potencial de valorização de cotas e reajuste de aluguéis.",
                    },
                    {
                        "ticker": "BTLG11",
                        "name": "BTG Logística FII",
                        "asset_type": "FII",
                        "current_price": 101.50,
                        "target_weight_pct": 7.0,
                        "expected_yield_pct": 9.00,
                        "risk_level": "moderate",
                        "reason": "Estratégia ativa de reciclagem e aquisição de galpões logísticos last-mile no estado de São Paulo.",
                    },
                ],
            },
            {
                "asset_type": "TESOURO_DIRETO",
                "label": "Tesouro Direto",
                "target_weight_pct": 10.0,
                "description": "Títulos longos com alta duration para captura de marcação a mercado.",
                "assets": [
                    {
                        "ticker": "Tesouro IPCA+ 2045",
                        "name": "Tesouro IPCA+ 2045 (NTN-B Principal)",
                        "asset_type": "TESOURO_DIRETO",
                        "current_price": 1150.0,
                        "target_weight_pct": 10.0,
                        "expected_yield_pct": 6.60,
                        "risk_level": "moderate",
                        "reason": "Título de longa duration que oferece expressivo potencial de valorização de capital em ciclos de corte da taxa de juros.",
                    },
                ],
            },
        ],
    },
}


async def _enrich_prices_from_db(portfolio_data: dict, db: AsyncSession | None) -> dict:
    """Opcionalmente atualiza as cotações mais recentes do banco para os ativos conhecidos."""
    if db is None:
        return portfolio_data

    try:
        tickers = []
        for c in portfolio_data.get("classes", []):
            for a in c.get("assets", []):
                t = a.get("ticker", "").strip().upper()
                if t:
                    tickers.append(t)

        if not tickers:
            return portfolio_data

        # Busca os ativos cadastrados
        assets_res = await db.execute(
            select(Asset).where(Asset.ticker.in_(tickers))
        )
        assets_map = {a.ticker.upper(): a.id for a in assets_res.scalars().all()}

        if not assets_map:
            return portfolio_data

        # Para cada ativo encontrado, busca o preço mais recente
        for c in portfolio_data.get("classes", []):
            for a in c.get("assets", []):
                t = a.get("ticker", "").strip().upper()
                asset_id = assets_map.get(t)
                if asset_id:
                    price_res = await db.execute(
                        select(AssetPrice)
                        .where(AssetPrice.asset_id == asset_id)
                        .order_by(desc(AssetPrice.timestamp))
                        .limit(1)
                    )
                    latest_price = price_res.scalar_one_or_none()
                    if latest_price and latest_price.close > 0:
                        a["current_price"] = round(float(latest_price.close), 2)
    except Exception as exc:
        logger.warning("[RecommendedPortfolio] Erro ao enriquecer preços do banco: %s", exc)

    return portfolio_data


class RecommendedPortfolioService:
    @classmethod
    async def list_recommended_portfolios(
        cls, db: AsyncSession | None = None
    ) -> list[RecommendedPortfolio]:
        result: list[RecommendedPortfolio] = []
        for key in ["patrimonio", "proventos", "performance"]:
            raw = dict(RAW_PORTFOLIOS[key])
            enriched = await _enrich_prices_from_db(raw, db)
            result.append(RecommendedPortfolio(**enriched))
        return result

    @classmethod
    async def get_recommended_portfolio(
        cls, strategy: str, db: AsyncSession | None = None
    ) -> Optional[RecommendedPortfolio]:
        strat = strategy.lower().strip()
        if strat not in RAW_PORTFOLIOS:
            return None
        raw = dict(RAW_PORTFOLIOS[strat])
        enriched = await _enrich_prices_from_db(raw, db)
        return RecommendedPortfolio(**enriched)

    @classmethod
    async def simulate_contribution(
        cls, request: RecommendedPortfolioSimulationRequest, db: AsyncSession | None = None
    ) -> RecommendedPortfolioSimulationResponse:
        portfolio = await cls.get_recommended_portfolio(request.strategy, db)
        if not portfolio:
            # Fallback para patrimonio se estratégia desconhecida
            portfolio = await cls.get_recommended_portfolio("patrimonio", db)

        assert portfolio is not None

        custom_weights = request.custom_class_weights or {}
        # Mapeia pesos por asset_type
        target_weights: dict[str, float] = {}

        if custom_weights:
            total_custom = sum(max(0.0, float(w)) for w in custom_weights.values())
            if total_custom > 0:
                for k, v in custom_weights.items():
                    target_weights[k.upper()] = (max(0.0, float(v)) / total_custom) * 100.0
            else:
                for c in portfolio.classes:
                    target_weights[c.asset_type] = c.target_weight_pct
        else:
            for c in portfolio.classes:
                target_weights[c.asset_type] = c.target_weight_pct

        total_amount = round(float(request.total_amount), 2)
        classes_simulated: list[SimulatedClassAllocation] = []

        for c in portfolio.classes:
            class_weight = target_weights.get(c.asset_type, c.target_weight_pct)
            class_allocated_amount = round(total_amount * (class_weight / 100.0), 2)

            simulated_assets: list[SimulatedAssetAllocation] = []
            assets_total_weight = sum(a.target_weight_pct for a in c.assets) or 1.0

            for a in c.assets:
                asset_share_in_class = a.target_weight_pct / assets_total_weight
                asset_allocated_amount = round(class_allocated_amount * asset_share_in_class, 2)
                cur_price = a.current_price if a.current_price > 0 else 1.0
                suggested_qty = round(asset_allocated_amount / cur_price, 4)

                simulated_assets.append(
                    SimulatedAssetAllocation(
                        ticker=a.ticker,
                        name=a.name,
                        asset_type=a.asset_type,
                        current_price=a.current_price,
                        weight_in_portfolio_pct=round((asset_allocated_amount / total_amount) * 100.0, 2) if total_amount > 0 else 0.0,
                        allocated_amount=asset_allocated_amount,
                        suggested_quantity=suggested_qty,
                        reason=a.reason,
                    )
                )

            classes_simulated.append(
                SimulatedClassAllocation(
                    asset_type=c.asset_type,
                    label=c.label,
                    target_weight_pct=round(class_weight, 2),
                    allocated_amount=class_allocated_amount,
                    assets=simulated_assets,
                )
            )

        # Ajuste de centavos no primeiro ativo
        total_allocated = sum(
            a.allocated_amount for cls_sim in classes_simulated for a in cls_sim.assets
        )
        diff = round(total_amount - total_allocated, 2)
        if diff != 0 and classes_simulated and classes_simulated[0].assets:
            classes_simulated[0].assets[0].allocated_amount = round(
                classes_simulated[0].assets[0].allocated_amount + diff, 2
            )
            classes_simulated[0].allocated_amount = round(
                classes_simulated[0].allocated_amount + diff, 2
            )

        strategy_labels = {
            "patrimonio": "Aumento e Preservação de Patrimônio",
            "proventos": "Renda Passiva e Fluxo de Proventos",
            "performance": "Performance e Crescimento",
        }
        strat_name = strategy_labels.get(portfolio.strategy, portfolio.title)

        summary_text = (
            f"Simulação para aporte de R$ {total_amount:,.2f} na estratégia '{strat_name}'. "
            f"O capital foi distribuído proporcionalmente entre {len(classes_simulated)} classes de ativos, "
            f"assegurando aderência às teses da IA e maximizando a relação risco-retorno."
        )

        return RecommendedPortfolioSimulationResponse(
            strategy=portfolio.strategy,
            total_amount=total_amount,
            classes=classes_simulated,
            summary=summary_text,
        )
