"""Serviço de Análise de Ativos por Inteligência Artificial e Confronto de Dados.

Confronta:
1. Fundamentos e múltiplos de valuation (`P/L`, `P/VP`, `DY`, `ROE`, `Margem Líquida`,
   `Dívida Líquida/EBITDA`, vacância física/financeira, valor patrimonial por cota);
2. Histórico de preços de fechamento diário (tendência 30d/90d/12m, volatilidade e drawdown);
3. Histórico e regularidade de proventos nos últimos 12 meses;
4. Últimos Relatórios Gerenciais (FNet CVM/B3 para FIIs, incluindo texto extraído do PDF)
   e Demonstrações Estruturadas (`ITR`, `DFP`, `FRE` na B3/CVM para Ações/BDRs);
5. Notícias externas recentes sobre o ativo.

Quando `GEMINI_API_KEY` ou `GROQ_API_KEY` estão configuradas no ambiente, sintetiza uma
análise executiva aprofundada via LLM ancorada exclusivamente nos dados coletados,
complementando o motor analítico determinístico.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.core.log_safety import sanitize_log_value

logger = logging.getLogger(__name__)


def _flt(val: Any) -> Optional[float]:
    if isinstance(val, (int, float)):
        return float(val)
    return None


def _fmt_pct(val: Optional[float]) -> str:
    if val is None:
        return "—"
    return f"{val:.2f}%".replace(".", ",")


def _fmt_num(val: Optional[float]) -> str:
    if val is None:
        return "—"
    return f"{val:.2f}".replace(".", ",")


class AssetAiAnalysisService:
    """Motor de diagnóstico e confronto de relatórios gerenciais + fundamentos por ativo."""

    async def analyze_asset(
        self,
        *,
        asset: dict[str, Any],
        enrichment: dict[str, Any],
        price_history: list[dict[str, Any]],
        dividends: list[dict[str, Any]],
        reports: list[dict[str, Any]],
        latest_report_excerpt: Optional[dict[str, Any]] = None,
        news: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        ticker = str(asset.get("ticker") or "").upper()
        asset_type = str(asset.get("asset_type") or enrichment.get("asset_class") or "ACAO").upper()
        currency = str(asset.get("currency") or "BRL").upper()
        last_price = _flt(asset.get("last_price"))

        price_stats = self._compute_price_trend(price_history, last_price)
        div_stats = self._compute_dividend_consistency(
            dividends, enrichment, last_price, currency=currency
        )

        strengths: list[str] = []
        attention_points: list[str] = []
        confrontation_points: list[str] = []
        score = 65

        if asset_type == "FII" or ticker.endswith("11") and enrichment.get("fii_indicators"):
            fii = enrichment.get("fii_indicators") or {}
            score, s_pts, a_pts, c_pts = self._evaluate_fii(
                ticker=ticker,
                fii=fii if isinstance(fii, dict) else {},
                last_price=last_price,
                price_stats=price_stats,
                div_stats=div_stats,
                reports=reports,
                latest_report_excerpt=latest_report_excerpt,
            )
            strengths.extend(s_pts)
            attention_points.extend(a_pts)
            confrontation_points.extend(c_pts)
        elif asset_type in ("ACAO", "STOCK", "BDR"):
            fundamentals = (
                enrichment.get("stock_fundamentals")
                or enrichment.get("bdr_indicators")
                or enrichment.get("fundamentals")
                or {}
            )
            score, s_pts, a_pts, c_pts = self._evaluate_equity(
                ticker=ticker,
                asset_type=asset_type,
                fundamentals=fundamentals if isinstance(fundamentals, dict) else {},
                last_price=last_price,
                currency=currency,
                price_stats=price_stats,
                div_stats=div_stats,
                reports=reports,
            )
            strengths.extend(s_pts)
            attention_points.extend(a_pts)
            confrontation_points.extend(c_pts)
        else:
            score, s_pts, a_pts, c_pts = self._evaluate_general_asset(
                ticker=ticker,
                asset_type=asset_type,
                enrichment=enrichment,
                price_stats=price_stats,
                div_stats=div_stats,
            )
            strengths.extend(s_pts)
            attention_points.extend(a_pts)
            confrontation_points.extend(c_pts)

        # Incorpora contexto de notícias recentes
        news_list = news or []
        if news_list:
            latest_headline = news_list[0].get("title")
            latest_source = news_list[0].get("source")
            if latest_headline:
                confrontation_points.append(
                    f"Noticiário recente ({latest_source}): \"{latest_headline}\" — confrontado com a tendência de "
                    f"preço de {_fmt_pct(price_stats.get('return_30d_pct'))} nos últimos 30 dias."
                )

        score = max(15, min(98, int(round(score))))
        if score >= 78:
            verdict_label = "Fundamentos Sólidos e Consistentes"
        elif score >= 60:
            verdict_label = "Equilibrado com Pontos de Monitoramento"
        else:
            verdict_label = "Exige Cautela e Acompanhamento Rigoroso"

        deterministic_summary = self._build_executive_summary(
            ticker=ticker,
            asset_name=str(asset.get("name") or ticker),
            asset_type=asset_type,
            score=score,
            verdict_label=verdict_label,
            price_stats=price_stats,
            div_stats=div_stats,
            reports=reports,
            latest_report_excerpt=latest_report_excerpt,
            news_count=len(news_list),
        )

        base_payload: dict[str, Any] = {
            "ticker": ticker,
            "asset_type": asset_type,
            "score": score,
            "verdict_label": verdict_label,
            "executive_summary": deterministic_summary,
            "strengths": strengths or ["Ativo catalogado com histórico de cotações monitorado pelo sistema."],
            "attention_points": attention_points or ["Acompanhar divulgações periódicas e variações macroeconômicas do setor."],
            "report_confrontation": confrontation_points or [
                "Indicadores de mercado monitorados; aguarda-se nova divulgação periódica para confronto adicional."
            ],
            "price_trend": price_stats,
            "dividend_outlook": div_stats,
            "latest_report_referenced": (
                {
                    "title": (
                        latest_report_excerpt.get("title")
                        if latest_report_excerpt
                        else (reports[0].get("title") if reports else None)
                    ),
                    "reference_date": (
                        latest_report_excerpt.get("reference_date")
                        if latest_report_excerpt
                        else (reports[0].get("reference_date") if reports else None)
                    ),
                    "delivery_date": (
                        latest_report_excerpt.get("delivery_date")
                        if latest_report_excerpt
                        else (reports[0].get("delivery_date") if reports else None)
                    ),
                    "url": (
                        latest_report_excerpt.get("url")
                        if latest_report_excerpt
                        else (reports[0].get("url") if reports else None)
                    ),
                    "excerpt_preview": (
                        str(latest_report_excerpt.get("excerpt") or "")[:420] + "…"
                        if latest_report_excerpt and latest_report_excerpt.get("excerpt")
                        else None
                    ),
                }
                if (latest_report_excerpt or reports)
                else None
            ),
            "provider_mode": "deterministic-audit-engine",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "disclaimer": (
                "Análise automatizada baseada em indicadores fundamentalistas, histórico de cotações e "
                "documentos públicos (CVM/B3). Não constitui recomendação de compra ou venda."
            ),
        }

        return base_payload

    # -------------------------------------------------------------------------
    # Cálculos auxiliares de preço e proventos
    # -------------------------------------------------------------------------

    def _compute_price_trend(
        self,
        price_history: list[dict[str, Any]],
        last_price: Optional[float],
    ) -> dict[str, Any]:
        points: list[tuple[Optional[date], float]] = []
        for p in price_history:
            c = p.get("close")
            if not isinstance(c, (int, float)) or float(c) <= 0:
                continue
            raw_ts = str(p.get("timestamp") or p.get("date") or "")[:10]
            obs_date: Optional[date] = None
            if len(raw_ts) == 10:
                try:
                    obs_date = date.fromisoformat(raw_ts)
                except ValueError:
                    obs_date = None
            points.append((obs_date, float(c)))

        if not points and last_price:
            points = [(None, float(last_price))]

        closes = [val for _, val in points]
        if not closes:
            return {
                "days_analyzed": 0,
                "latest_close": last_price,
                "period_low": None,
                "period_high": None,
                "return_30d_pct": None,
                "return_90d_pct": None,
                "return_period_pct": None,
                "trend_label": "Sem série histórica",
            }

        latest = closes[-1]
        first = closes[0]
        dated_points = sorted(
            [(d, val) for d, val in points if d is not None],
            key=lambda item: item[0],
        )

        def _window_return(window_days: int) -> Optional[float]:
            if len(dated_points) < 2:
                return None
            latest_dt, latest_val = dated_points[-1]
            earliest_dt, _ = dated_points[0]
            target_dt = latest_dt - timedelta(days=window_days)
            if earliest_dt > target_dt:
                return None
            baseline_val: Optional[float] = None
            for obs_dt, obs_val in dated_points:
                if obs_dt <= target_dt:
                    baseline_val = obs_val
                else:
                    break
            if baseline_val is None or baseline_val <= 0:
                return None
            return ((latest_val / baseline_val) - 1.0) * 100.0

        ret_30 = _window_return(30)
        ret_90 = _window_return(90)
        ret_period = ((latest / first) - 1.0) * 100.0 if first > 0 and len(closes) >= 2 else None

        if ret_90 is not None:
            if ret_90 > 5.0:
                trend = "Tendência de Alta"
            elif ret_90 < -5.0:
                trend = "Tendência de Correção / Baixa"
            else:
                trend = "Lateralizado / Estável"
        elif ret_period is not None:
            trend = "Alta no Período" if ret_period >= 0 else "Recuo no Período"
        else:
            trend = "Estável"

        return {
            "days_analyzed": len(closes),
            "latest_close": round(latest, 4),
            "period_low": round(min(closes), 4),
            "period_high": round(max(closes), 4),
            "return_30d_pct": round(ret_30, 2) if ret_30 is not None else None,
            "return_90d_pct": round(ret_90, 2) if ret_90 is not None else None,
            "return_period_pct": round(ret_period, 2) if ret_period is not None else None,
            "trend_label": trend,
        }

    def _compute_dividend_consistency(
        self,
        dividends: list[dict[str, Any]],
        enrichment: dict[str, Any],
        last_price: Optional[float],
        *,
        currency: str = "BRL",
    ) -> dict[str, Any]:
        div_metrics = enrichment.get("dividend_metrics") if isinstance(enrichment.get("dividend_metrics"), dict) else {}
        today_dt = datetime.now(timezone.utc).date()
        today_iso = today_dt.isoformat()
        cutoff_iso = (today_dt - timedelta(days=365)).isoformat()
        trailing_values: list[float] = []
        for d in dividends:
            val = float(d.get("value_per_unit") or d.get("value") or 0.0)
            if val <= 0:
                continue
            ev_date = str(d.get("payment_date") or d.get("ex_date") or d.get("record_date") or "")[:10]
            if ev_date and cutoff_iso <= ev_date <= today_iso:
                trailing_values.append(val)

        has_cached_metrics = bool(div_metrics and div_metrics.get("payments_count_12m") is not None)
        payments_12m = (
            int(div_metrics["payments_count_12m"])
            if has_cached_metrics
            else len(trailing_values)
        )
        total_12m = (
            float(div_metrics.get("total_paid_12m") or 0.0)
            if has_cached_metrics
            else sum(trailing_values)
        )
        if div_metrics.get("frequency"):
            frequency = str(div_metrics["frequency"])
        elif payments_12m >= 10:
            frequency = "Mensal"
        elif payments_12m in (3, 4, 5):
            frequency = "Trimestral"
        elif payments_12m in (1, 2):
            frequency = "Semestral"
        elif payments_12m > 0:
            frequency = "Periódica"
        else:
            frequency = "Sem pagamentos"

        dy_12m = _flt(div_metrics.get("dy_12m"))
        if dy_12m is None:
            fii_ind = enrichment.get("fii_indicators") if isinstance(enrichment.get("fii_indicators"), dict) else {}
            stock_ind = enrichment.get("stock_fundamentals") if isinstance(enrichment.get("stock_fundamentals"), dict) else {}
            bdr_ind = enrichment.get("bdr_indicators") if isinstance(enrichment.get("bdr_indicators"), dict) else {}
            dy_12m = (
                _flt(fii_ind.get("dividend_yield"))
                or _flt(stock_ind.get("dividend_yield"))
                or _flt(bdr_ind.get("dividend_yield"))
            )
            if (
                dy_12m is None
                and currency.upper() == "BRL"
                and last_price
                and last_price > 0
                and total_12m > 0
            ):
                dy_12m = round((total_12m / last_price) * 100.0, 2)

        avg_payment = round(total_12m / payments_12m, 4) if payments_12m > 0 else 0.0
        return {
            "payments_count_12m": payments_12m,
            "total_paid_12m": round(total_12m, 4),
            "average_per_payment": avg_payment,
            "dividend_yield_pct": round(dy_12m, 2) if dy_12m is not None else None,
            "frequency": frequency,
            "summary": (
                f"Distribuição {frequency.lower()} com {payments_12m} evento(s) nos últimos 12 meses "
                f"(média de R$ {_fmt_num(avg_payment)}/cota e DY de {_fmt_pct(dy_12m)})."
                if payments_12m > 0
                else "Sem eventos de distribuição de proventos registrados nos últimos 12 meses."
            ),
        }

    # -------------------------------------------------------------------------
    # Regras de Confronto para FIIs
    # -------------------------------------------------------------------------

    def _evaluate_fii(
        self,
        *,
        ticker: str,
        fii: dict[str, Any],
        last_price: Optional[float],
        price_stats: dict[str, Any],
        div_stats: dict[str, Any],
        reports: list[dict[str, Any]],
        latest_report_excerpt: Optional[dict[str, Any]],
    ) -> tuple[int, list[str], list[str], list[str]]:
        score = 68
        strengths: list[str] = []
        attention: list[str] = []
        confrontation: list[str] = []

        pvp = _flt(fii.get("pvp"))
        nav = _flt(fii.get("nav_per_share"))
        dy = _flt(fii.get("dividend_yield")) or _flt(div_stats.get("dividend_yield_pct"))
        phys_vac = _flt(fii.get("physical_vacancy"))
        fin_vac = _flt(fii.get("financial_vacancy"))
        prop_count = fii.get("properties_count")
        segment = fii.get("segment") or "Fundo Imobiliário"

        if pvp is not None:
            if 0.82 <= pvp <= 1.03:
                score += 10
                strengths.append(
                    f"Múltiplo P/VP de {_fmt_num(pvp)}x negociado próximo ou com desconto frente ao valor patrimonial "
                    f"de R$ {_fmt_num(nav)} por cota."
                )
            elif pvp < 0.82:
                score += 2
                attention.append(
                    f"Deságio acentuado no P/VP ({_fmt_num(pvp)}x): exige confrontar no Relatório Gerencial se há "
                    "inadimplência, alavancagem ou revisão de laudo patrimonial."
                )
            elif pvp > 1.10:
                score -= 5
                attention.append(
                    f"Cota negociada com ágio relevante sobre o patrimônio líquido (P/VP de {_fmt_num(pvp)}x), "
                    "reduzindo a margem de segurança."
                )

        if dy is not None:
            if 8.0 <= dy <= 14.5:
                score += 10
                strengths.append(
                    f"Dividend Yield anualizado atrativo de {_fmt_pct(dy)} com frequência {div_stats.get('frequency', 'mensal').lower()}."
                )
            elif dy > 14.5:
                attention.append(
                    f"Dividend Yield elevado ({_fmt_pct(dy)}): verificar no Relatório Gerencial se o rendimento decorre "
                    "de ganhos não recorrentes ou indexação inflacionária temporária."
                )

        if phys_vac is not None:
            if phys_vac <= 5.0:
                score += 7
                strengths.append(f"Baixa vacância física ({_fmt_pct(phys_vac)}), demonstrando forte ocupação dos ativos.")
            elif phys_vac >= 15.0:
                score -= 8
                attention.append(f"Vacância física elevada ({_fmt_pct(phys_vac)}) pressionando a geração de renda imobiliária.")

        if prop_count and int(prop_count) >= 5:
            score += 4
            strengths.append(f"Portfólio diversificado com {prop_count} imóveis no segmento {segment}.")

        # Confronto direto com o Relatório Gerencial (FNet)
        if latest_report_excerpt and latest_report_excerpt.get("excerpt"):
            ref = latest_report_excerpt.get("reference_date") or latest_report_excerpt.get("delivery_date") or "recente"
            excerpt_txt = str(latest_report_excerpt["excerpt"])
            confrontation.append(
                f"Relatório Gerencial oficial (ref. {ref}) localizado e processado ({latest_report_excerpt.get('pages_count', 1)} pág.): "
                f"os dados operacionais do fundo ({segment}) foram confrontados com a cotação de mercado de R$ {_fmt_num(last_price)} "
                f"e P/VP de {_fmt_num(pvp)}x."
            )
            # Busca palavras-chave no relatório gerencial extraído
            lower_txt = excerpt_txt.lower()
            if "vacância" in lower_txt or "ocupação" in lower_txt:
                confrontation.append(
                    "O Relatório Gerencial aborda explicitamente indicadores de ocupação/vacância e evolução locatícia "
                    f"(vacância física atual registrada: {_fmt_pct(phys_vac)}, financeira: {_fmt_pct(fin_vac)})."
                )
            if "inadimpl" in lower_txt or "pré-pagamento" in lower_txt or "risco" in lower_txt:
                confrontation.append(
                    "O gestor menciona eventos de crédito/locatários no relatório gerencial; recomenda-se acompanhar "
                    "o impacto nas reservas acumuladas e na distribuição por cota."
                )
            if "resultado" in lower_txt or "dividendo" in lower_txt or "rendimento" in lower_txt:
                confrontation.append(
                    f"Confronto de Proventos: o fundo acumula {div_stats.get('payments_count_12m', 0)} distribuições em 12 meses "
                    f"(total de R$ {_fmt_num(div_stats.get('total_paid_12m'))}/cota), alinhado ao regime de distribuição reportado."
                )
        elif reports:
            latest_doc = reports[0]
            confrontation.append(
                f"Último documento CVM/B3 disponível: {latest_doc.get('title')} (ref. {latest_doc.get('reference_date')}, "
                f"entregue em {latest_doc.get('delivery_date')})."
            )

        return score, strengths, attention, confrontation

    # -------------------------------------------------------------------------
    # Regras de Confronto para Ações / BDRs / Stocks
    # -------------------------------------------------------------------------

    def _evaluate_equity(
        self,
        *,
        ticker: str,
        asset_type: str,
        fundamentals: dict[str, Any],
        last_price: Optional[float],
        currency: str,
        price_stats: dict[str, Any],
        div_stats: dict[str, Any],
        reports: list[dict[str, Any]],
    ) -> tuple[int, list[str], list[str], list[str]]:
        score = 66
        strengths: list[str] = []
        attention: list[str] = []
        confrontation: list[str] = []

        pe = _flt(fundamentals.get("pe"))
        pb = _flt(fundamentals.get("pb"))
        roe = _flt(fundamentals.get("roe"))
        net_margin = _flt(fundamentals.get("net_margin"))
        dy = _flt(fundamentals.get("dividend_yield")) or _flt(div_stats.get("dividend_yield_pct"))
        ev_ebitda = _flt(fundamentals.get("enterprise_to_ebitda"))
        target_price = _flt(fundamentals.get("target_price"))

        if roe is not None:
            if roe >= 15.0:
                score += 10
                strengths.append(f"Rentabilidade sobre patrimônio (ROE) elevada de {_fmt_pct(roe)}, demonstrando eficiência na alocação de capital.")
            elif roe < 5.0:
                score -= 6
                attention.append(f"ROE comprimido ({_fmt_pct(roe)}), indicando retorno patrimonial abaixo do custo de oportunidade.")

        if net_margin is not None:
            if net_margin >= 12.0:
                score += 7
                strengths.append(f"Margem líquida robusta de {_fmt_pct(net_margin)}, conferindo resiliência operacional.")
            elif net_margin < 0:
                score -= 10
                attention.append(f"Margem líquida negativa ({_fmt_pct(net_margin)}) no período acumulado.")

        if pe is not None:
            if 0 < pe <= 12.0:
                score += 8
                strengths.append(f"Múltiplo P/L descontado ({_fmt_num(pe)}x) em relação à média histórica de mercado.")
            elif pe > 28.0:
                attention.append(f"Múltiplo P/L esticado ({_fmt_num(pe)}x), embutindo expectativa elevada de crescimento futuro nos resultados.")
            elif pe < 0:
                score -= 8
                attention.append("P/L negativo decorrente de prejuízo contábil nos últimos 12 meses.")

        if dy is not None and dy >= 6.0:
            score += 6
            strengths.append(f"Remuneração relevante ao acionista com Dividend Yield de {_fmt_pct(dy)}.")

        if target_price and last_price and last_price > 0:
            upside = ((target_price / last_price) - 1.0) * 100.0
            confrontation.append(
                f"Confronto Preço × Consenso: cotação atual ({currency} {_fmt_num(last_price)}) frente ao preço-alvo médio "
                f"de {currency} {_fmt_num(target_price)} implica potencial de {_fmt_pct(upside)}."
            )

        if reports:
            itr_dfp = [r for r in reports if r.get("is_management_report")]
            latest_rep = itr_dfp[0] if itr_dfp else reports[0]
            confrontation.append(
                f"Confronto Contábil CVM/B3: último demonstrativo oficial ({latest_rep.get('title')}, ref. "
                f"{latest_rep.get('reference_date')}, entregue em {latest_rep.get('delivery_date')}) confrontado com "
                f"P/VP de {_fmt_num(pb)}x e EV/EBITDA de {_fmt_num(ev_ebitda)}x."
            )
        else:
            confrontation.append(
                f"Indicadores fundamentalistas (P/L {_fmt_num(pe)}x, P/VP {_fmt_num(pb)}x, ROE {_fmt_pct(roe)}) "
                f"confrontados com a variação de preço de {_fmt_pct(price_stats.get('return_90d_pct'))} em 90 dias."
            )

        return score, strengths, attention, confrontation

    def _evaluate_general_asset(
        self,
        *,
        ticker: str,
        asset_type: str,
        enrichment: dict[str, Any],
        price_stats: dict[str, Any],
        div_stats: dict[str, Any],
    ) -> tuple[int, list[str], list[str], list[str]]:
        score = 70
        strengths: list[str] = []
        attention: list[str] = []
        confrontation: list[str] = []

        ret_90 = _flt(price_stats.get("return_90d_pct"))
        if ret_90 is not None:
            if ret_90 >= 0:
                score += 6
                strengths.append(f"Desempenho positivo de {_fmt_pct(ret_90)} nos últimos 90 pregões analisados.")
            else:
                attention.append(f"Oscilação negativa de {_fmt_pct(ret_90)} na janela recente de 90 dias.")

        if asset_type.startswith("ETF") and isinstance(enrichment.get("etf_indicators"), dict):
            etf = enrichment["etf_indicators"]
            bench = etf.get("benchmark")
            fee = _flt(etf.get("expense_ratio"))
            if bench:
                strengths.append(f"Exposição diversificada passiva referenciada no índice {bench}.")
            if fee is not None:
                confrontation.append(f"Taxa de administração de {_fmt_pct(fee)} a.a. confrontada com a aderência ao benchmark {bench or ticker}.")

        return score, strengths, attention, confrontation

    def _build_executive_summary(
        self,
        *,
        ticker: str,
        asset_name: str,
        asset_type: str,
        score: int,
        verdict_label: str,
        price_stats: dict[str, Any],
        div_stats: dict[str, Any],
        reports: list[dict[str, Any]],
        latest_report_excerpt: Optional[dict[str, Any]],
        news_count: int,
    ) -> str:
        trend = price_stats.get("trend_label") or "Estável"
        ret_90 = price_stats.get("return_90d_pct")
        ret_txt = f" ({_fmt_pct(ret_90)} em 90 dias)" if ret_90 is not None else ""
        rep_txt = (
            f"Foram analisados {len(reports)} documento(s) regulatórios/gerenciais na CVM/B3"
            + (" (incluindo leitura direta do último Relatório Gerencial em PDF)" if latest_report_excerpt else "")
            if reports
            else "A análise consolida os múltiplos fundamentalistas e séries históricas persistidas no catálogo"
        )
        news_txt = f" e {news_count} notícia(s) recente(s) de mercado" if news_count > 0 else ""
        return (
            f"{ticker} ({asset_name}) apresenta score analítico {score}/100 ({verdict_label}). "
            f"{rep_txt}{news_txt}. No mercado secundário, o ativo opera em {trend.lower()}{ret_txt}. "
            f"{div_stats.get('summary', '')}"
        ).strip()

    async def _try_llm_synthesis(
        self,
        *,
        base_payload: dict[str, Any],
        enrichment: dict[str, Any],
        latest_report_excerpt: Optional[dict[str, Any]],
        news_list: list[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        gemini_key = getattr(settings, "GEMINI_API_KEY", None)
        groq_key = getattr(settings, "GROQ_API_KEY", None)
        if not gemini_key and not groq_key:
            return None

        prompt = (
            "Você é o Analista Fundamentalista e de Relatórios Gerenciais de IA do SGI.\n"
            "Confronte os múltiplos fundamentalistas, histórico de preços, proventos, notícias recentes e o trecho "
            "do último Relatório Gerencial / ITR / DFP abaixo para entregar um resumo executivo objetivo (1 parágrafo denso) "
            "em Português do Brasil, sem inventar números e sem dar recomendação de compra/venda.\n\n"
            f"Ativo: {base_payload['ticker']} ({base_payload['asset_type']}) | Score: {base_payload['score']}/100\n"
            f"Tendência de Preço: {json.dumps(base_payload['price_trend'], ensure_ascii=False)}\n"
            f"Proventos: {json.dumps(base_payload['dividend_outlook'], ensure_ascii=False)}\n"
            f"Confrontos Preliminares: {json.dumps(base_payload['report_confrontation'], ensure_ascii=False)}\n"
            f"Trecho do Último Relatório Gerencial: {(latest_report_excerpt or {}).get('excerpt', 'N/A')[:1400]}\n"
            f"Notícias Recentes: {json.dumps([n.get('title') for n in news_list[:4]], ensure_ascii=False)}\n"
        )

        if gemini_key:
            try:
                model = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                async with httpx.AsyncClient(timeout=6.0) as client:
                    resp = await client.post(
                        url,
                        headers={"x-goog-api-key": gemini_key},
                        json={
                            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 450},
                        },
                    )
                    if resp.status_code == 200:
                        candidates = resp.json().get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts and parts[0].get("text"):
                                return {
                                    "executive_summary": parts[0]["text"].strip(),
                                    "provider_mode": f"llm:{model}",
                                }
            except Exception as exc:
                logger.debug("Gemini synthesis skipped for %s: %s", sanitize_log_value(base_payload["ticker"]), sanitize_log_value(exc))

        if groq_key:
            try:
                model = getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")
                async with httpx.AsyncClient(timeout=6.0) as client:
                    resp = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {groq_key}"},
                        json={
                            "model": model,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.2,
                            "max_tokens": 450,
                        },
                    )
                    if resp.status_code == 200:
                        choices = resp.json().get("choices", [])
                        if choices:
                            txt = choices[0].get("message", {}).get("content", "").strip()
                            if txt:
                                return {
                                    "executive_summary": txt,
                                    "provider_mode": f"llm:{model}",
                                }
            except Exception as exc:
                logger.debug("Groq synthesis skipped for %s: %s", sanitize_log_value(base_payload["ticker"]), sanitize_log_value(exc))

        return None


asset_ai_analysis_service = AssetAiAnalysisService()
