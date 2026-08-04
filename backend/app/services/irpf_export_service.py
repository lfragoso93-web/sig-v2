"""Exportadores PDF e CSV do IRPF canônico."""

from datetime import UTC, datetime
from io import BytesIO

from app.services.irpf_canonical_export_service import IrpfCanonicalExport


def _today_label() -> str:
    return datetime.now(UTC).date().strftime("%d/%m/%Y")


def generate_irpf_pdf(report: IrpfCanonicalExport) -> bytes:
    """Gera PDF do relatório IRPF canônico e retorna os bytes do arquivo."""

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as exc:
        raise RuntimeError(
            "reportlab nao instalado. Adicione 'reportlab' ao requirements.txt."
        ) from exc

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=16,
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontSize=13,
        spaceAfter=8,
        spaceBefore=14,
    )
    normal = styles["Normal"]
    header_color = colors.HexColor("#1e3a5f")
    alternate_color = colors.HexColor("#f0f4f8")

    def table(data, column_widths=None):
        result = Table(data, colWidths=column_widths, repeatRows=1)
        result.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), header_color),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, alternate_color],
                    ),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return result

    def brl(value):
        return (
            f"R$ {value:,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    story = [
        Paragraph(f"Relatorio IRPF {report.year}", title_style),
        Paragraph(
            f"Carteira ID: {report.portfolio_id} | Gerado em: {_today_label()}",
            normal,
        ),
        Spacer(1, 0.4 * cm),
        Paragraph("Resumo Anual Canônico", heading_style),
        table(
            [
                ["Descricao", "Valor"],
                ["Total Bens e Direitos (31/12)", brl(report.total_bens_direitos_brl)],
                ["Total Vendas no Ano", brl(report.total_vendas_ano_brl)],
                ["Imposto Bruto", brl(report.total_gross_tax_due_brl)],
                ["IRRF Compensado", brl(report.total_withholding_brl)],
                ["DARF Liberada", brl(report.total_payment_due_brl)],
                ["Total Dividendos Isentos", brl(report.total_dividendos_brl)],
                ["Total JCP Bruto", brl(report.total_jcp_bruto_brl)],
                ["IR Retido JCP (15%)", brl(report.total_jcp_ir_retido_brl)],
                [
                    "Prejuizo Day Trade a Compensar",
                    brl(report.closing_day_trade_loss_carryforward_brl),
                ],
            ],
            column_widths=[11 * cm, 5 * cm],
        ),
    ]
    story.extend([PageBreak(), Paragraph("Bens e Direitos (posicao em 31/12)", heading_style)])
    if report.bens_direitos:
        rows = [["Codigo", "Ticker", "Tipo", "Qtd", "Custo Medio", "Custo Total"]]
        rows.extend(
            [
                item.codigo_irpf,
                item.ticker,
                item.asset_type,
                f"{item.quantidade:,.4f}",
                brl(item.custo_medio),
                brl(item.custo_total),
            ]
            for item in report.bens_direitos
        )
        story.append(
            table(
                rows,
                column_widths=[2 * cm, 3 * cm, 3.5 * cm, 2.5 * cm, 3.5 * cm, 3.5 * cm],
            )
        )
    else:
        story.append(Paragraph("Nenhuma posicao encontrada.", normal))

    story.extend([PageBreak(), Paragraph("Ganhos de Capital Mensais", heading_style)])
    for monthly in report.ganhos_mensais:
        story.append(Paragraph(f"Mes: {monthly.mes}", styles["Heading3"]))
        story.append(
            table(
                [
                    [
                        "Total Vendas",
                        "Lucro Bruto",
                        "Isencao",
                        "Base Calc.",
                        "IR Swing",
                        "IR DT",
                        "IR a Recolher",
                    ],
                    [
                        brl(monthly.total_vendas),
                        brl(monthly.lucro_bruto),
                        brl(monthly.isencao_aplicada),
                        brl(monthly.base_calculo),
                        brl(monthly.ir_devido_swing),
                        brl(monthly.ir_devido_day_trade),
                        brl(monthly.ir_a_recolher),
                    ],
                ]
            )
        )
        story.append(Spacer(1, 0.3 * cm))
    if not report.ganhos_mensais:
        story.append(Paragraph("Nenhuma venda no ano.", normal))

    story.extend([PageBreak(), Paragraph("Rendimentos Isentos - Dividendos", heading_style)])
    if report.dividendos:
        rows = [["Ticker", "Tipo", "Total Recebido", "Qtd Pagamentos"]]
        rows.extend(
            [item.ticker, item.asset_type, brl(item.total_recebido), str(item.quantidade_pgtos)]
            for item in report.dividendos
        )
        story.append(table(rows, column_widths=[4 * cm, 4 * cm, 5 * cm, 4 * cm]))
    else:
        story.append(Paragraph("Nenhum dividendo recebido no ano.", normal))

    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("JCP - Juros sobre Capital Proprio", heading_style))
    if report.jcp:
        rows = [["Ticker", "Total Bruto", "IR Retido (15%)", "Total Liquido"]]
        rows.extend(
            [item.ticker, brl(item.total_bruto), brl(item.ir_retido), brl(item.total_liquido)]
            for item in report.jcp
        )
        story.append(table(rows, column_widths=[4 * cm, 4.5 * cm, 4.5 * cm, 4.5 * cm]))
    else:
        story.append(Paragraph("Nenhum JCP no ano.", normal))

    document.build(story)
    return buffer.getvalue()


def generate_irpf_csv(report: IrpfCanonicalExport) -> str:
    """Gera CSV canônico com separador ponto-e-vírgula para locale PT-BR."""

    import csv
    from io import StringIO

    buffer = StringIO()
    writer = csv.writer(buffer, delimiter=";", quotechar='"', lineterminator="\n")

    def brl(value):
        return (
            f"{value:,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    writer.writerow(["RELATÓRIO IRPF", report.year])
    writer.writerow(["Carteira ID", report.portfolio_id])
    writer.writerow(["Gerado em", _today_label()])
    writer.writerow([])
    writer.writerow(["RESUMO ANUAL CANÔNICO"])
    writer.writerow(["Descricao", "Valor"])
    writer.writerow(["Total Bens e Direitos (31/12)", brl(report.total_bens_direitos_brl)])
    writer.writerow(["Total Vendas no Ano", brl(report.total_vendas_ano_brl)])
    writer.writerow(["Imposto Bruto", brl(report.total_gross_tax_due_brl)])
    writer.writerow(["IRRF Compensado", brl(report.total_withholding_brl)])
    writer.writerow(["DARF Liberada", brl(report.total_payment_due_brl)])
    writer.writerow(["Total Dividendos Isentos", brl(report.total_dividendos_brl)])
    writer.writerow(["Total JCP Bruto", brl(report.total_jcp_bruto_brl)])
    writer.writerow(["IR Retido JCP (15%)", brl(report.total_jcp_ir_retido_brl)])
    writer.writerow(
        [
            "Prejuizo Day Trade a Compensar",
            brl(report.closing_day_trade_loss_carryforward_brl),
        ]
    )
    writer.writerow([])

    writer.writerow(["BENS E DIREITOS (posicao em 31/12)"])
    writer.writerow(
        [
            "Codigo IRPF",
            "Ticker",
            "Tipo",
            "Quantidade",
            "Custo Medio",
            "Custo Total",
            "Moeda",
        ]
    )
    for item in report.bens_direitos:
        writer.writerow(
            [
                item.codigo_irpf,
                item.ticker,
                item.asset_type,
                f"{item.quantidade:,.4f}".replace(",", "X").replace(".", ",").replace("X", "."),
                brl(item.custo_medio),
                brl(item.custo_total),
                item.moeda,
            ]
        )
    if report.bens_direitos:
        writer.writerow(["TOTAL", "", "", "", "", brl(report.total_bens_direitos_brl), ""])
    writer.writerow([])

    writer.writerow(["GANHOS DE CAPITAL MENSAIS"])
    for monthly in report.ganhos_mensais:
        writer.writerow([f"MES: {monthly.mes}"])
        writer.writerow(
            [
                "Total Vendas",
                "Lucro Bruto",
                "Isencao Aplicada",
                "Base Calculo",
                "IR Swing",
                "IR Day Trade",
                "IR a Recolher",
            ]
        )
        writer.writerow(
            [
                brl(monthly.total_vendas),
                brl(monthly.lucro_bruto),
                brl(monthly.isencao_aplicada),
                brl(monthly.base_calculo),
                brl(monthly.ir_devido_swing),
                brl(monthly.ir_devido_day_trade),
                brl(monthly.ir_a_recolher),
            ]
        )
        writer.writerow(["VENDAS DETALHADAS"])
        writer.writerow(
            [
                "Data",
                "Ticker",
                "Tipo",
                "Quantidade",
                "Preco Venda",
                "Custo Aquisicao",
                "Lucro/Prejuizo",
                "Day Trade?",
                "Isento?",
            ]
        )
        for sale in monthly.vendas:
            writer.writerow(
                [
                    sale.data,
                    sale.ticker,
                    sale.asset_type,
                    f"{sale.quantidade:,.4f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    brl(sale.preco_venda),
                    brl(sale.custo_aquisicao),
                    brl(sale.lucro_bruto),
                    "SIM" if sale.is_day_trade else "NAO",
                    "SIM" if sale.is_isento else "NAO",
                ]
            )
        writer.writerow([])
    writer.writerow([])

    writer.writerow(["DIVIDENDOS ISENTOS"])
    writer.writerow(["Ticker", "Tipo", "Total Recebido", "Numero Pagamentos"])
    for item in report.dividendos:
        writer.writerow(
            [item.ticker, item.asset_type, brl(item.total_recebido), str(item.quantidade_pgtos)]
        )
    if report.dividendos:
        writer.writerow(["TOTAL", "", brl(report.total_dividendos_brl), ""])
    writer.writerow([])

    writer.writerow(["JCP - JUROS SOBRE CAPITAL PROPRIO"])
    writer.writerow(["Ticker", "Total Bruto", "IR Retido (15%)", "Total Liquido"])
    for item in report.jcp:
        writer.writerow(
            [
                item.ticker,
                brl(item.total_bruto),
                brl(item.ir_retido),
                brl(item.total_liquido),
            ]
        )
    if report.jcp:
        writer.writerow(
            [
                "TOTAL",
                brl(report.total_jcp_bruto_brl),
                brl(report.total_jcp_ir_retido_brl),
                brl(sum(item.total_liquido for item in report.jcp)),
            ]
        )

    return buffer.getvalue()
