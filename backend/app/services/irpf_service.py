"""
Servico de calculo de IRPF para carteiras de investimento.

Cobre:
  - Bens e Direitos (posicao em 31/12)
  - Ganhos de Capital mensais com isenção de R$20k para acoes
  - Deteccao de Day Trade por logica (mesmo dia + ticker + buy+sell)
  - Ativos internacionais com conversao BRL pela taxa da data
  - Rendimentos Isentos (dividendos)
  - JCP (15% retido na fonte)
  - Geracao de PDF via reportlab
  - Persistencia do relatorio em IRPFReport.data (JSON)

Aliquotas (vigentes 2024-base):
  Swing Trade acoes/FIIs:  15%
  Swing Trade ETFs/INTL:   15%
  Day Trade (todos):       20%
  Isencao acoes swing:     vendas mensais <= R$20.000
  JCP retencao:            15%
"""
import logging
from collections import defaultdict
from datetime import date, datetime, timezone
from io import BytesIO

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.irpf import IRPFReport
from app.models.transaction import Transaction, OperationType
from app.services.canonical_dividend_entitlement import EntitlementReason
from app.services.canonical_dividend_entitlement_reader import (
    load_portfolio_dividend_entitlements,
)
from app.schemas.irpf import (
    BemDireito,
    VendaMensal,
    GanhoCapitalMensal,
    RendimentoIsento,
    JCPItem,
    IRPFResumo,
    IRPFReportOut,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

ALIQ_SWING = 0.15
ALIQ_DAY_TRADE = 0.20
ISENCAO_ACOES_MENSAL = 20_000.0

# Codigos IRPF por tipo de ativo
_CODIGO_IRPF: dict[str, tuple[str, str]] = {
    "ACAO":              ("31", "03 - Participacoes Societarias"),
    "FII":               ("73", "07 - Fundos"),
    "ETF":               ("74", "07 - Fundos"),
    "ETF_INTERNACIONAL": ("74", "07 - Fundos"),
    "STOCK":             ("31", "03 - Participacoes Societarias"),
    "BDR":               ("35", "03 - Participacoes Societarias"),
    "CRIPTO":            ("08", "08 - Criptoativos"),
    "TESOURO_DIRETO":    ("45", "04 - Aplicacoes e Investimentos"),
    "RENDA_FIXA":        ("45", "04 - Aplicacoes e Investimentos"),
}

# Tipos de acao para regra de isencao 20k
_ACAO_TYPES = {"ACAO", "STOCK", "BDR"}
# Tipos internacionais (requerem conversao de moeda)
_INTL_TYPES = {"STOCK", "ETF_INTERNACIONAL"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _codigo_irpf(asset_type: str) -> tuple[str, str]:
    return _CODIGO_IRPF.get(asset_type.upper(), ("99", "09 - Outros"))


def _detect_day_trades(txs: list) -> set[tuple[date, str]]:
    """
    Retorna set de (date, ticker) onde houve Day Trade:
    existem tanto compra quanto venda do mesmo ticker no mesmo dia.
    """
    by_day: dict[tuple[date, str], set[str]] = defaultdict(set)
    for tx in txs:
        op = tx.operation.value if isinstance(tx.operation, OperationType) else str(tx.operation)
        by_day[(tx.date, tx.ticker)].add(op)
    return {
        key for key, ops in by_day.items()
        if "buy" in ops and "sell" in ops
    }


async def _get_usd_brl_rate(tx_date: date) -> float:
    """
    Retorna taxa USD/BRL na data da transacao.
    Tenta via price_history_service; fallback para 1.0 com log de aviso.
    """
    try:
        from app.services.price_history_service import get_price_at_date
        from app.models.asset import AssetType
        rate = await get_price_at_date(None, "USDBRL=X", AssetType.ETF_INTERNACIONAL, str(tx_date))
        if rate and rate > 0:
            return rate
    except Exception as e:
        logger.warning(f"[IRPF] falha ao buscar USD/BRL em {tx_date}: {e}")
    logger.warning(f"[IRPF] usando taxa USD/BRL=1.0 para {tx_date} (nao encontrada)")
    return 1.0


# ---------------------------------------------------------------------------
# Bens e Direitos
# ---------------------------------------------------------------------------

async def calc_bens_direitos(
    db: AsyncSession,
    portfolio_id: int,
    year: int,
) -> list[BemDireito]:
    """
    Calcula posicao de cada ativo em 31/12/year com custo medio ponderado.
    Inclui ativos zerados (vendidos no ano) com custo_total = 0.
    """
    cutoff = date(year, 12, 31)

    result = await db.execute(
        select(Transaction).where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.date <= cutoff,
        ).order_by(Transaction.date.asc())
    )
    txs = result.scalars().all()

    positions: dict[str, dict] = {}

    for tx in txs:
        t = tx.ticker
        op = tx.operation.value if isinstance(tx.operation, OperationType) else str(tx.operation)
        at = (tx.asset_type or "").upper()
        currency = getattr(tx, "currency", "BRL") or "BRL"

        price_brl = tx.price
        if currency != "BRL" and at in _INTL_TYPES:
            rate = await _get_usd_brl_rate(tx.date)
            price_brl = tx.price * rate

        fees = getattr(tx, "fees", 0.0) or 0.0
        total_cost = price_brl * tx.quantity + fees

        if t not in positions:
            positions[t] = {"qty": 0.0, "cost": 0.0, "asset_type": at, "currency": currency}

        if op == "buy":
            positions[t]["qty"] += tx.quantity
            positions[t]["cost"] += total_cost
        elif op == "sell" and positions[t]["qty"] > 0:
            avg = positions[t]["cost"] / positions[t]["qty"]
            positions[t]["qty"] = max(0.0, positions[t]["qty"] - tx.quantity)
            positions[t]["cost"] = positions[t]["qty"] * avg

    bens = []
    for ticker, pos in positions.items():
        if pos["qty"] <= 0:
            continue
        at = pos["asset_type"]
        codigo, grupo = _codigo_irpf(at)
        custo_medio = pos["cost"] / pos["qty"] if pos["qty"] > 0 else 0.0
        bens.append(BemDireito(
            ticker=ticker,
            nome=ticker,
            asset_type=at,
            codigo_irpf=codigo,
            grupo_irpf=grupo,
            quantidade=round(pos["qty"], 6),
            custo_medio=round(custo_medio, 2),
            custo_total=round(pos["cost"], 2),
            moeda=pos["currency"],
        ))

    return sorted(bens, key=lambda b: (b.grupo_irpf, b.ticker))


# ---------------------------------------------------------------------------
# Ganhos de Capital
# ---------------------------------------------------------------------------

async def calc_ganhos_capital(
    db: AsyncSession,
    portfolio_id: int,
    year: int,
) -> list[GanhoCapitalMensal]:
    """
    Calcula ganhos/perdas de capital para cada mes do ano.
    Aplica:
      - Isencao de R$20k para acoes em swing trade
      - Aliquota 20% para Day Trade
      - Aliquota 15% para swing (acoes, FIIs, ETFs)
      - Compensacao de prejuizo acumulado entre meses
    """
    start = date(year, 1, 1)
    end = date(year, 12, 31)

    all_tx_result = await db.execute(
        select(Transaction).where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.date >= start,
            Transaction.date <= end,
        ).order_by(Transaction.date.asc())
    )
    all_txs = all_tx_result.scalars().all()
    day_trade_keys = _detect_day_trades(all_txs)

    prev_result = await db.execute(
        select(Transaction).where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.date < start,
        ).order_by(Transaction.date.asc())
    )
    prev_txs = prev_result.scalars().all()

    avg_costs: dict[str, dict] = {}
    for tx in prev_txs:
        t = tx.ticker
        op = tx.operation.value if isinstance(tx.operation, OperationType) else str(tx.operation)
        at = (tx.asset_type or "").upper()
        currency = getattr(tx, "currency", "BRL") or "BRL"
        price_brl = tx.price
        if currency != "BRL" and at in _INTL_TYPES:
            rate = await _get_usd_brl_rate(tx.date)
            price_brl = tx.price * rate
        fees = getattr(tx, "fees", 0.0) or 0.0
        cost = price_brl * tx.quantity + fees
        if t not in avg_costs:
            avg_costs[t] = {"qty": 0.0, "cost": 0.0, "asset_type": at}
        if op == "buy":
            avg_costs[t]["qty"] += tx.quantity
            avg_costs[t]["cost"] += cost
        elif op == "sell" and avg_costs[t]["qty"] > 0:
            avg = avg_costs[t]["cost"] / avg_costs[t]["qty"]
            avg_costs[t]["qty"] = max(0.0, avg_costs[t]["qty"] - tx.quantity)
            avg_costs[t]["cost"] = avg_costs[t]["qty"] * avg

    vendas_por_mes: dict[str, list] = defaultdict(list)
    compras_no_ano: dict[str, dict] = {}

    for tx in all_txs:
        t = tx.ticker
        at = (tx.asset_type or "").upper()
        op = tx.operation.value if isinstance(tx.operation, OperationType) else str(tx.operation)
        currency = getattr(tx, "currency", "BRL") or "BRL"
        price_brl = tx.price
        if currency != "BRL" and at in _INTL_TYPES:
            rate = await _get_usd_brl_rate(tx.date)
            price_brl = tx.price * rate
        fees = getattr(tx, "fees", 0.0) or 0.0
        cost = price_brl * tx.quantity + fees

        if t not in avg_costs:
            avg_costs[t] = {"qty": 0.0, "cost": 0.0, "asset_type": at}
        if t not in compras_no_ano:
            compras_no_ano[t] = {"qty": avg_costs[t]["qty"], "cost": avg_costs[t]["cost"]}

        if op == "buy":
            avg_costs[t]["qty"] += tx.quantity
            avg_costs[t]["cost"] += cost
        elif op == "sell" and avg_costs[t]["qty"] > 0:
            avg = avg_costs[t]["cost"] / avg_costs[t]["qty"] if avg_costs[t]["qty"] > 0 else 0.0
            custo_venda = avg * tx.quantity
            lucro = price_brl * tx.quantity - custo_venda - fees
            is_dt = (tx.date, t) in day_trade_keys
            mes = tx.date.strftime("%Y-%m")
            vendas_por_mes[mes].append({
                "ticker": t,
                "asset_type": at,
                "data": str(tx.date),
                "quantidade": tx.quantity,
                "preco_venda": round(price_brl, 2),
                "custo_aquisicao": round(avg, 2),
                "lucro_bruto": round(lucro, 2),
                "is_day_trade": is_dt,
                "total_venda_brl": round(price_brl * tx.quantity, 2),
            })
            avg_costs[t]["qty"] = max(0.0, avg_costs[t]["qty"] - tx.quantity)
            avg_costs[t]["cost"] = avg_costs[t]["qty"] * avg

    prejuizo_acumulado = 0.0
    resultado: list[GanhoCapitalMensal] = []

    for mes in sorted(vendas_por_mes.keys()):
        vendas = vendas_por_mes[mes]

        swing_acoes = [v for v in vendas if not v["is_day_trade"] and v["asset_type"] in _ACAO_TYPES]
        swing_outros = [v for v in vendas if not v["is_day_trade"] and v["asset_type"] not in _ACAO_TYPES]
        day_trades = [v for v in vendas if v["is_day_trade"]]

        total_vendas_acoes = sum(v["total_venda_brl"] for v in swing_acoes)
        isencao = total_vendas_acoes if total_vendas_acoes <= ISENCAO_ACOES_MENSAL else 0.0

        lucro_swing_acoes = sum(v["lucro_bruto"] for v in swing_acoes)
        lucro_swing_outros = sum(v["lucro_bruto"] for v in swing_outros)
        lucro_swing = lucro_swing_acoes + lucro_swing_outros
        lucro_dt = sum(v["lucro_bruto"] for v in day_trades)

        base_swing = max(0.0, lucro_swing - isencao)

        if base_swing > 0 and prejuizo_acumulado < 0:
            compensacao = min(base_swing, abs(prejuizo_acumulado))
            base_swing -= compensacao
            prejuizo_acumulado += compensacao

        if base_swing < 0:
            prejuizo_acumulado += base_swing
            base_swing = 0.0

        base_dt = max(0.0, lucro_dt)

        ir_swing = round(base_swing * ALIQ_SWING, 2)
        ir_dt = round(base_dt * ALIQ_DAY_TRADE, 2)

        total_vendas = sum(v["total_venda_brl"] for v in vendas)
        total_custo = sum(v["custo_aquisicao"] * v["quantidade"] for v in vendas)
        ir_retido = 0.0

        vendas_out = []
        for v in vendas:
            eh_isento = (
                not v["is_day_trade"]
                and v["asset_type"] in _ACAO_TYPES
                and total_vendas_acoes <= ISENCAO_ACOES_MENSAL
            )
            vendas_out.append(VendaMensal(
                ticker=v["ticker"],
                asset_type=v["asset_type"],
                data=v["data"],
                quantidade=v["quantidade"],
                preco_venda=v["preco_venda"],
                custo_aquisicao=v["custo_aquisicao"],
                lucro_bruto=v["lucro_bruto"],
                is_day_trade=v["is_day_trade"],
                is_isento=eh_isento,
                ir_retido=0.0,
            ))

        resultado.append(GanhoCapitalMensal(
            mes=mes,
            total_vendas=round(total_vendas, 2),
            total_custo=round(total_custo, 2),
            lucro_bruto=round(lucro_swing + lucro_dt, 2),
            lucro_day_trade=round(lucro_dt, 2),
            lucro_swing_trade=round(lucro_swing, 2),
            isencao_aplicada=round(isencao, 2),
            base_calculo=round(base_swing + base_dt, 2),
            aliquota_swing=ALIQ_SWING,
            aliquota_day_trade=ALIQ_DAY_TRADE,
            ir_devido_swing=ir_swing,
            ir_devido_day_trade=ir_dt,
            ir_retido_fonte=ir_retido,
            ir_a_recolher=round(ir_swing + ir_dt - ir_retido, 2),
            vendas=vendas_out,
        ))

    return resultado


# ---------------------------------------------------------------------------
# Rendimentos
# ---------------------------------------------------------------------------

async def calc_rendimentos(
    db: AsyncSession,
    portfolio_id: int,
    year: int,
) -> tuple[list[RendimentoIsento], list[JCPItem]]:
    """Return exempt dividends and JCP from canonical BRL entitlements."""
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    entitlements = await load_portfolio_dividend_entitlements(
        db,
        portfolio_id,
    )

    dividendos: dict[str, dict] = {}
    jcp: dict[str, dict] = {}

    for item in entitlements:
        payment_date = item.event.payment_date
        if (
            item.entitlement.reason is not EntitlementReason.ELIGIBLE
            or item.entitlement.currency != "BRL"
            or payment_date is None
            or not start <= payment_date <= end
        ):
            continue

        ticker = item.ticker
        if item.event.event_type.upper() == "JCP":
            values = jcp.setdefault(
                ticker,
                {"bruto": 0.0, "retido": 0.0, "liquido": 0.0},
            )
            values["bruto"] += float(item.entitlement.gross_amount)
            values["retido"] += float(item.entitlement.withholding_tax)
            values["liquido"] += float(item.entitlement.net_amount)
        else:
            values = dividendos.setdefault(
                ticker,
                {"total": 0.0, "count": 0, "asset_type": item.asset_type},
            )
            values["total"] += float(item.entitlement.net_amount)
            values["count"] += 1

    div_list = [
        RendimentoIsento(
            ticker=t,
            asset_type=v.get("asset_type", ""),
            total_recebido=round(v["total"], 2),
            quantidade_pgtos=v["count"],
        )
        for t, v in sorted(dividendos.items())
    ]

    jcp_list = [
        JCPItem(
            ticker=t,
            total_bruto=round(v["bruto"], 2),
            ir_retido=round(v["retido"], 2),
            total_liquido=round(v["liquido"], 2),
        )
        for t, v in sorted(jcp.items())
    ]

    return div_list, jcp_list


# ---------------------------------------------------------------------------
# Orquestrador principal
# ---------------------------------------------------------------------------

async def generate_irpf_report(
    db: AsyncSession,
    portfolio_id: int,
    year: int,
) -> IRPFReportOut:
    """
    Gera relatorio IRPF completo, persiste em IRPFReport e retorna o schema.
    Se ja existir relatorio para o ano, sobrescreve.
    """
    bens = await calc_bens_direitos(db, portfolio_id, year)
    ganhos = await calc_ganhos_capital(db, portfolio_id, year)
    dividendos, jcp = await calc_rendimentos(db, portfolio_id, year)

    total_ir_swing = sum(g.ir_devido_swing for g in ganhos)
    total_ir_dt = sum(g.ir_devido_day_trade for g in ganhos)
    total_ir_retido = sum(g.ir_retido_fonte for g in ganhos)
    prejuizo = sum(
        g.lucro_swing_trade for g in ganhos if g.lucro_swing_trade < 0
    )

    resumo = IRPFResumo(
        ano=year,
        total_bens_direitos=round(sum(b.custo_total for b in bens), 2),
        total_vendas_ano=round(sum(g.total_vendas for g in ganhos), 2),
        lucro_tributavel_swing=round(sum(g.base_calculo for g in ganhos), 2),
        lucro_tributavel_day_trade=round(sum(g.lucro_day_trade for g in ganhos if g.lucro_day_trade > 0), 2),
        ir_swing_trade_devido=round(total_ir_swing, 2),
        ir_day_trade_devido=round(total_ir_dt, 2),
        ir_retido_fonte_total=round(total_ir_retido, 2),
        ir_a_recolher_total=round(total_ir_swing + total_ir_dt - total_ir_retido, 2),
        total_dividendos_isentos=round(sum(d.total_recebido for d in dividendos), 2),
        total_jcp_bruto=round(sum(j.total_bruto for j in jcp), 2),
        total_jcp_ir_retido=round(sum(j.ir_retido for j in jcp), 2),
        prejuizo_acumulado=round(prejuizo, 2),
    )

    report_out = IRPFReportOut(
        portfolio_id=portfolio_id,
        ano=year,
        bens_direitos=bens,
        ganhos_mensais=ganhos,
        dividendos=dividendos,
        jcp=jcp,
        resumo=resumo,
    )

    existing = await db.execute(
        select(IRPFReport).where(
            IRPFReport.portfolio_id == portfolio_id,
            IRPFReport.year == year,
        )
    )
    report_row = existing.scalar_one_or_none()
    data_json = report_out.model_dump_json()

    if report_row is None:
        report_row = IRPFReport(
            portfolio_id=portfolio_id,
            year=year,
            data=data_json,
        )
        db.add(report_row)
    else:
        report_row.data = data_json
        report_row.created_at = datetime.now(timezone.utc)

    await db.commit()
    return report_out


# ---------------------------------------------------------------------------
# Geracao de PDF
# ---------------------------------------------------------------------------

def generate_irpf_pdf(report: IRPFReportOut) -> bytes:
    """
    Gera PDF do relatorio IRPF usando reportlab.
    Retorna bytes prontos para download.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
        )
    except ImportError:
        raise RuntimeError("reportlab nao instalado. Adicione 'reportlab' ao requirements.txt.")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=16, spaceAfter=12)
    h2_style = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13, spaceAfter=8, spaceBefore=14)
    normal = styles["Normal"]

    HEADER_COLOR = colors.HexColor("#1e3a5f")
    ALT_COLOR = colors.HexColor("#f0f4f8")
    WHITE = colors.white

    def _table(data, col_widths=None):
        t = Table(data, colWidths=col_widths, repeatRows=1)
        style = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_COLOR),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, ALT_COLOR]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
        t.setStyle(style)
        return t

    def brl(v): return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    story = []

    story.append(Paragraph(f"Relatorio IRPF {report.ano}", title_style))
    story.append(Paragraph(f"Carteira ID: {report.portfolio_id} | Gerado em: {date.today().strftime('%d/%m/%Y')}", normal))
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("Resumo Anual", h2_style))
    r = report.resumo
    resumo_data = [
        ["Descricao", "Valor"],
        ["Total Bens e Direitos (31/12)", brl(r.total_bens_direitos)],
        ["Total Vendas no Ano", brl(r.total_vendas_ano)],
        ["Lucro Tributavel Swing Trade", brl(r.lucro_tributavel_swing)],
        ["Lucro Tributavel Day Trade", brl(r.lucro_tributavel_day_trade)],
        ["IR Swing Trade Devido", brl(r.ir_swing_trade_devido)],
        ["IR Day Trade Devido", brl(r.ir_day_trade_devido)],
        ["IR Retido na Fonte", brl(r.ir_retido_fonte_total)],
        ["IR a Recolher", brl(r.ir_a_recolher_total)],
        ["Total Dividendos Isentos", brl(r.total_dividendos_isentos)],
        ["Total JCP Bruto", brl(r.total_jcp_bruto)],
        ["IR Retido JCP (15%)", brl(r.total_jcp_ir_retido)],
        ["Prejuizo Acumulado", brl(r.prejuizo_acumulado)],
    ]
    story.append(_table(resumo_data, col_widths=[11 * cm, 5 * cm]))
    story.append(PageBreak())

    story.append(Paragraph("Bens e Direitos (posicao em 31/12)", h2_style))
    if report.bens_direitos:
        bd_data = [["Codigo", "Ticker", "Tipo", "Qtd", "Custo Medio", "Custo Total"]]
        for b in report.bens_direitos:
            bd_data.append([b.codigo_irpf, b.ticker, b.asset_type,
                            f"{b.quantidade:,.4f}", brl(b.custo_medio), brl(b.custo_total)])
        story.append(_table(bd_data, col_widths=[2*cm, 3*cm, 3.5*cm, 2.5*cm, 3.5*cm, 3.5*cm]))
    else:
        story.append(Paragraph("Nenhuma posicao encontrada.", normal))
    story.append(PageBreak())

    story.append(Paragraph("Ganhos de Capital Mensais", h2_style))
    for gm in report.ganhos_mensais:
        story.append(Paragraph(f"Mes: {gm.mes}", styles["Heading3"]))
        gm_data = [
            ["Total Vendas", "Lucro Bruto", "Isencao", "Base Calc.", "IR Swing", "IR DT", "IR a Recolher"],
            [brl(gm.total_vendas), brl(gm.lucro_bruto), brl(gm.isencao_aplicada),
             brl(gm.base_calculo), brl(gm.ir_devido_swing), brl(gm.ir_devido_day_trade), brl(gm.ir_a_recolher)],
        ]
        story.append(_table(gm_data))
        story.append(Spacer(1, 0.3 * cm))
    if not report.ganhos_mensais:
        story.append(Paragraph("Nenhuma venda no ano.", normal))
    story.append(PageBreak())

    story.append(Paragraph("Rendimentos Isentos - Dividendos", h2_style))
    if report.dividendos:
        div_data = [["Ticker", "Tipo", "Total Recebido", "Qtd Pagamentos"]]
        for d in report.dividendos:
            div_data.append([d.ticker, d.asset_type, brl(d.total_recebido), str(d.quantidade_pgtos)])
        story.append(_table(div_data, col_widths=[4*cm, 4*cm, 5*cm, 4*cm]))
    else:
        story.append(Paragraph("Nenhum dividendo recebido no ano.", normal))
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("JCP - Juros sobre Capital Proprio", h2_style))
    if report.jcp:
        jcp_data = [["Ticker", "Total Bruto", "IR Retido (15%)", "Total Liquido"]]
        for j in report.jcp:
            jcp_data.append([j.ticker, brl(j.total_bruto), brl(j.ir_retido), brl(j.total_liquido)])
        story.append(_table(jcp_data, col_widths=[4*cm, 4.5*cm, 4.5*cm, 4.5*cm]))
    else:
        story.append(Paragraph("Nenhum JCP no ano.", normal))

    doc.build(story)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Geracao de CSV
# ---------------------------------------------------------------------------

def generate_irpf_csv(report: IRPFReportOut) -> str:
    """
    Gera CSV do relatorio IRPF com multiplas secoes.
    Retorna string CSV com separador ponto-virgula para compatibilidade com Excel PT-BR.
    """
    import csv
    from io import StringIO

    buffer = StringIO()
    writer = csv.writer(buffer, delimiter=';', quotechar='"', lineterminator='\n')

    def brl(v):
        return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    r = report.resumo

    writer.writerow(["RELATÓRIO IRPF", report.ano])
    writer.writerow(["Carteira ID", report.portfolio_id])
    writer.writerow(["Gerado em", date.today().strftime('%d/%m/%Y')])
    writer.writerow([])

    writer.writerow(["RESUMO ANUAL"])
    writer.writerow(["Descricao", "Valor"])
    writer.writerow(["Total Bens e Direitos (31/12)", brl(r.total_bens_direitos)])
    writer.writerow(["Total Vendas no Ano", brl(r.total_vendas_ano)])
    writer.writerow(["Lucro Tributavel Swing Trade", brl(r.lucro_tributavel_swing)])
    writer.writerow(["Lucro Tributavel Day Trade", brl(r.lucro_tributavel_day_trade)])
    writer.writerow(["IR Swing Trade Devido", brl(r.ir_swing_trade_devido)])
    writer.writerow(["IR Day Trade Devido", brl(r.ir_day_trade_devido)])
    writer.writerow(["IR Retido na Fonte", brl(r.ir_retido_fonte_total)])
    writer.writerow(["IR a Recolher", brl(r.ir_a_recolher_total)])
    writer.writerow(["Total Dividendos Isentos", brl(r.total_dividendos_isentos)])
    writer.writerow(["Total JCP Bruto", brl(r.total_jcp_bruto)])
    writer.writerow(["IR Retido JCP (15%)", brl(r.total_jcp_ir_retido)])
    writer.writerow(["Prejuizo Acumulado", brl(r.prejuizo_acumulado)])
    writer.writerow([])

    writer.writerow(["BENS E DIREITOS (posicao em 31/12)"])
    writer.writerow(["Codigo IRPF", "Ticker", "Tipo", "Quantidade", "Custo Medio", "Custo Total", "Moeda"])
    if report.bens_direitos:
        for b in report.bens_direitos:
            writer.writerow([
                b.codigo_irpf,
                b.ticker,
                b.asset_type,
                f"{b.quantidade:,.4f}".replace(",", "X").replace(".", ",").replace("X", "."),
                brl(b.custo_medio),
                brl(b.custo_total),
                b.moeda,
            ])
        total_bens = sum(b.custo_total for b in report.bens_direitos)
        writer.writerow(["TOTAL", "", "", "", "", brl(total_bens), ""])
    writer.writerow([])

    writer.writerow(["GANHOS DE CAPITAL MENSAIS"])
    for gm in report.ganhos_mensais:
        writer.writerow([f"MES: {gm.mes}"])
        writer.writerow(["Total Vendas", "Lucro Bruto", "Isencao Aplicada", "Base Calculo", "IR Swing", "IR Day Trade", "IR a Recolher"])
        writer.writerow([
            brl(gm.total_vendas),
            brl(gm.lucro_bruto),
            brl(gm.isencao_aplicada),
            brl(gm.base_calculo),
            brl(gm.ir_devido_swing),
            brl(gm.ir_devido_day_trade),
            brl(gm.ir_a_recolher),
        ])
        writer.writerow(["VENDAS DETALHADAS"])
        writer.writerow(["Data", "Ticker", "Tipo", "Quantidade", "Preco Venda", "Custo Aquisicao", "Lucro/Prejuizo", "Day Trade?", "Isento?"])
        for v in gm.vendas:
            writer.writerow([
                v.data,
                v.ticker,
                v.asset_type,
                f"{v.quantidade:,.4f}".replace(",", "X").replace(".", ",").replace("X", "."),
                brl(v.preco_venda),
                brl(v.custo_aquisicao),
                brl(v.lucro_bruto),
                "SIM" if v.is_day_trade else "NAO",
                "SIM" if v.is_isento else "NAO",
            ])
        writer.writerow([])
    writer.writerow([])

    writer.writerow(["DIVIDENDOS ISENTOS"])
    writer.writerow(["Ticker", "Tipo", "Total Recebido", "Numero Pagamentos"])
    if report.dividendos:
        for d in report.dividendos:
            writer.writerow([
                d.ticker,
                d.asset_type,
                brl(d.total_recebido),
                str(d.quantidade_pgtos),
            ])
        total_div = sum(d.total_recebido for d in report.dividendos)
        writer.writerow(["TOTAL", "", brl(total_div), ""])
    writer.writerow([])

    writer.writerow(["JCP - JUROS SOBRE CAPITAL PROPRIO"])
    writer.writerow(["Ticker", "Total Bruto", "IR Retido (15%)", "Total Liquido"])
    if report.jcp:
        for j in report.jcp:
            writer.writerow([
                j.ticker,
                brl(j.total_bruto),
                brl(j.ir_retido),
                brl(j.total_liquido),
            ])
        total_jcp = sum(j.total_bruto for j in report.jcp)
        writer.writerow(["TOTAL", brl(total_jcp), brl(sum(j.ir_retido for j in report.jcp)), brl(sum(j.total_liquido for j in report.jcp))])

    return buffer.getvalue()
