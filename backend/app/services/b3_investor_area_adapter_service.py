"""Adapter para arquivos exportados pela Área do Investidor B3 (CSV, XLSX e PDF).

Converte arquivos de negociação e movimentação da B3 no formato/DTO canônico
de importação do SGI v2 sem acoplamento direto com persistência no banco.

Arquitetura obrigatória (Issue #358):
    arquivo B3 -> parser/adapter B3 -> DTO canônico de import -> validação/dry-run -> TransactionWriteService -> rebuild canônico
"""
from __future__ import annotations

import csv
import io
import math
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from app.models.asset import AssetType

try:
    import openpyxl
except ImportError:
    openpyxl = None  # type: ignore[assignment]

try:
    import pypdf
except ImportError:
    pypdf = None  # type: ignore[assignment]


_ODD_LOT_PATTERN = re.compile(r"^([A-Z]{4}\d{1,2})F$")
_B3_DATE_PATTERN = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
_TICKER_EXTRACT_PATTERN = re.compile(r"\b([A-Z]{4}\d{1,2}(?:F)?)\b")

MONTHS_PT = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}
_B3_PDF_DATE_SECTION_PATTERN = re.compile(
    r"^(\d{1,2})\s+de\s+([a-zA-ZçÇ]+)\s+de\s+(\d{4})",
    re.IGNORECASE,
)

# Eventos de proventos/ações corporativas e ajustes que não devem gerar compras/vendas financeiras
_CORPORATE_OR_INCOME_KEYWORDS = {
    "DIVIDENDO",
    "JUROS SOBRE CAPITAL PROPRIO",
    "JUROS SOBRE CAPITAL PRÓPRIO",
    "JSCP",
    "JCP",
    "RENDIMENTO",
    "DIREITO DE SUBSCRICAO",
    "DIREITO DE SUBSCRIÇÃO",
    "DIREITOS DE SUBSCRICAO",
    "DIREITOS DE SUBSCRIÇÃO",
    "DIREITOS DE SUBSCRIÇÃO - NÃO EXERCIDO",
    "DIREITOS DE SUBSCRICAO - NAO EXERCIDO",
    "RECIBO DE SUBSCRICAO",
    "RECIBO DE SUBSCRIÇÃO",
    "AMORTIZACAO",
    "AMORTIZAÇÃO",
    "LEILAO DE FRACOES",
    "LEILÃO DE FRAÇÕES",
    "LEILAO DE FRACAO",
    "LEILÃO DE FRAÇÃO",
    "EMPRESTIMO",
    "EMPRÉSTIMO",
    "REEMBOLSO",
    "CESSAO DE DIREITOS",
    "CESSÃO DE DIREITOS",
    "SUB-ROGACAO",
    "SUB-ROGAÇÃO",
    "DIVIDENDO - CANCELADO",
    "RESGATE DE COTAS",
}

# Eventos corporativos de custódia que alteram quantidade de cotas/ações (desdobro, bonificação, atualização)
_CUSTODY_EVENT_KEYWORDS = {
    "DESDOBRO",
    "BONIFICACAO",
    "BONIFICAÇÃO",
    "BONIFICACAO EM ATIVOS",
    "BONIFICAÇÃO EM ATIVOS",
    "ATUALIZACAO",
    "ATUALIZAÇÃO",
    "FRACAO EM ATIVOS",
    "FRAÇÃO EM ATIVOS",
}

# Tickers conhecidos de ETFs nacionais terminados em 11
_KNOWN_ETF_11 = {
    "BOVA11", "SMAL11", "IVVB11", "HASH11", "DIVD11", "B5P211", "IMAB11",
    "IBOB11", "SPXI11", "NASD11", "XINA11", "DIVO11", "BRAX11", "ECOO11",
    "SMAC11", "MATB11", "FIND11", "ISUS11", "GENB11", "GOLD11", "AURO11",
    "COIN11", "QQQI11", "NDIV11", "NSDV11", "BBOV11", "XBOV11", "PIBB11",
    "BOVB11", "SMAB11", "SHOT11", "SPXB11", "TECB11", "UTEC11", "DNAI11",
}

# Tickers conhecidos de Units de Ações terminadas em 11
_KNOWN_STOCK_11 = {
    "SANB11", "TAEE11", "KLBN11", "ALUP11", "BPAC11", "ENGI11", "SAPR11",
    "CPLE11", "SULA11", "TIET11", "RNDP11", "MODL11", "BRBI11", "PPLA11",
}


@dataclass
class B3SkippedItem:
    line_number: int
    raw_ticker: str
    movement_type: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "line_number": self.line_number,
            "raw_ticker": self.raw_ticker,
            "movement_type": self.movement_type,
            "reason": self.reason,
        }


@dataclass
class B3AdaptResult:
    success: bool
    format_detected: str
    canonical_rows: list[dict[str, Any]] = field(default_factory=list)
    canonical_csv: str = ""
    skipped_items: list[B3SkippedItem] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def normalize_b3_ticker(raw_ticker: str) -> str:
    """Normaliza o ticker removendo razão social e sufixo fracionário 'F'."""
    cleaned = raw_ticker.strip().upper()
    if not cleaned:
        return ""

    if cleaned.startswith("TESOURO") or "TESOURO " in cleaned:
        # Normalizar títulos do Tesouro Direto:
        # "TESOURO SELIC 2029 - NTN-B" ou "TESOURO PREFIXADO 2027 INTER DISTRIBUIDORA DE TITULOS..." -> "TESOURO PREFIXADO 2027"
        match = re.search(r"^(TESOURO\s+.*?\b20\d{2}\b)", cleaned)
        if match:
            return match.group(1).strip()
        return cleaned.split("-")[0].strip()

    # Renda Fixa: manter código identificador limpo
    for rf_prefix in ("CDB", "LCI", "LCA", "CRI", "CRA", "DEB", "LIG", "LC", "RDB"):
        if cleaned.startswith(rf_prefix):
            # Ex: "CDB - CDBU2626QQS" ou "CDB - CDB926713G8 - BANCO INTER S/A" ou "CDB - CDBU2626QQS BANCO INTER S/A"
            parts = cleaned.split(" - ")
            if len(parts) >= 2:
                rf_code = parts[1].strip().split()[0].strip()
                return f"{parts[0].strip()} - {rf_code}"
            return parts[0].strip()

    # Procurar primeiro código padrão B3 (ex: PETR4, PETR4F, HGLG11)
    match = _TICKER_EXTRACT_PATTERN.search(cleaned)
    if match:
        token = match.group(1)
        odd_match = _ODD_LOT_PATTERN.match(token)
        if odd_match:
            return odd_match.group(1)
        return token

    # Fallback se não bater regex: remove traço
    token = cleaned.split("-")[0].strip()
    odd_match = _ODD_LOT_PATTERN.match(token)
    if odd_match:
        return odd_match.group(1)
    return token


def is_subscription_right_ticker(ticker: str, product_desc: str = "") -> bool:
    """Identifica se um ticker é um direito ou recibo temporário de subscrição na B3."""
    t = ticker.strip().upper()
    if re.match(r"^[A-Z]{4}(?:12|13|14)$", t):
        return True
    if re.match(r"^[A-Z]{4}(?:1|2|9|10)$", t):
        return True
    desc = product_desc.upper()
    if any(term in desc for term in ("SUBSCRICAO", "SUBSCRIÇÃO", "DIREITO DE SUBS", "RECIBO DE SUBS", "DIREITOS DE SUBS")):
        return True
    return False


def infer_b3_asset_type(ticker: str, product_name: str = "") -> str:
    """Infere o tipo de ativo com base no padrão do ticker e descrição do produto."""
    combined = f"{ticker} {product_name}".strip().upper()
    t = ticker.upper()

    if combined.startswith("TESOURO") or "TESOURO" in combined:
        return AssetType.TESOURO_DIRETO.value

    # Ticker padrão B3 de 4 letras + 11 (ex: VGIA11, VCRA11, DIVD11, TAEE11) não é título direto de Renda Fixa privada
    is_standard_equity_11 = bool(re.match(r"^[A-Z]{4}1[1-3]$", t))
    if not is_standard_equity_11:
        for rf_type in ("CDB", "LCI", "LCA", "CRI", "CRA", "DEBENTURE", "DEB", "LIG", "RDB", "LC "):
            if combined.startswith(rf_type) or f" {rf_type}" in combined:
                return AssetType.RENDA_FIXA.value

    # BDRs
    if t.endswith(("31", "32", "33", "34", "35", "39")) or " BDR" in combined or "- BDR" in combined:
        return AssetType.BDR.value

    # ETFs / Fundos de Índice
    etf_keywords = (
        "FDO DE INDICE", "FDO DE ÍNDICE", "FDO DE NDICE",
        "FUNDO DE INDICE", "FUNDO DE ÍNDICE", "FUNDO DE NDICE",
        "INDEX FUND", " ETF", "ETF ", "- ETF", "/ETF", "INDEX"
    )
    if any(k in combined for k in etf_keywords) or t in _KNOWN_ETF_11:
        return AssetType.ETF_NACIONAL.value

    # Units de Ações (ex: SANB11, TAEE11, KLBN11, ALUP11)
    # Empresas S.A. que não são fundos imobiliários/fiagros
    stock_keywords = (
        " S.A.", " S/A", " SA ", "COMPANHIA", "CIA ",
        "PARTICIPACOES", "PARTICIPAÇÕES", "INVESTIMENTO S/A",
        "UNIT", "UNT "
    )
    fii_negation_keywords = (
        "FDO INV IMOB", "FII", "FIAGRO", "IMOB", "IMOBILIARIO",
        "IMOBILIÁRIO", "REAL ESTATE", "HEDGE FUND"
    )
    if (
        (any(k in combined for k in stock_keywords) and not any(k in combined for k in fii_negation_keywords))
        or t in _KNOWN_STOCK_11
    ):
        return AssetType.ACAO.value

    # FIIs e FIAGROs
    fii_keywords = (
        "FDO INV IMOB", "FUNDO DE INVESTIMENTO IMOBILIARIO",
        "FUNDO DE INVESTIMENTO IMOBILIÁRIO", "FII", "FIAGRO",
        "IMOB", "IMOBILIARIO", "IMOBILIÁRIO", "REAL ESTATE",
        "HEDGE FUND", "RECEBIVEIS", "RECEBÍVEIS", "AGRO"
    )
    if any(k in combined for k in fii_keywords) or t.endswith("11"):
        return AssetType.FII.value

    # Ações regulares (terminadas em 3, 4, 5, 6, 7, 8)
    if any(t.endswith(s) for s in ("3", "4", "5", "6", "7", "8")):
        return AssetType.ACAO.value

    return AssetType.OUTRO.value


def parse_b3_number(raw_value: str) -> Decimal:
    """Converte valores numéricos no padrão brasileiro ('1.234,56' ou '35,50') para Decimal."""
    v = str(raw_value).strip().replace("R$", "").replace(" ", "")
    if not v or v == "-":
        return Decimal("0")
    if "," in v:
        v = v.replace(".", "").replace(",", ".")
    try:
        return Decimal(v)
    except InvalidOperation:
        return Decimal("0")


def parse_b3_date(raw_date: str) -> str:
    """Converte 'DD/MM/YYYY' ou 'DD de mês de YYYY' para 'YYYY-MM-DD'."""
    raw = str(raw_date).strip()
    match = _B3_DATE_PATTERN.match(raw)
    if match:
        day, month, year = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"

    # Tenta formato por extenso B3: "06 de novembro de 2026"
    dm = _B3_PDF_DATE_SECTION_PATTERN.match(raw)
    if dm:
        day, month_str, year = dm.groups()
        m_num = MONTHS_PT.get(month_str.lower(), 1)
        return f"{year}-{m_num:02d}-{int(day):02d}"

    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw
    raise ValueError(f"Data B3 inválida: '{raw}'")


def _detect_delimiter(sample_text: str) -> str:
    """Detecta o delimitador CSV provável (;, ,, ou tabulação)."""
    for line in sample_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if ";" in line:
            return ";"
        if "\t" in line:
            return "\t"
        if "," in line:
            return ","
    return ";"


def _normalize_header_name(header: str) -> str:
    h = str(header).strip().lower()
    h = (
        h.replace("á", "a")
        .replace("ã", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )
    return re.sub(r"[^a-z0-9_]", "", h.replace(" ", "_").replace("/", "_"))


def is_b3_csv_content(raw_content: str) -> bool:
    """Detecta rapidamente se o cabeçalho do arquivo corresponde à Área do Investidor B3."""
    if not raw_content or not raw_content.strip():
        return False
    first_lines = raw_content.strip().splitlines()[:5]
    for line in first_lines:
        line_norm = _normalize_header_name(line)
        if any(
            token in line_norm
            for token in (
                "negocio",
                "codigo_de_negociacao",
                "entrada_saida",
                "movimentacao",
                "produto",
            )
        ):
            return True
    return False


def is_b3_pdf_content(text: str) -> bool:
    """Detecta se o texto de um PDF corresponde à Área do Investidor B3."""
    if not text:
        return False
    upper = text.upper()
    return (
        "ACESSE INVESTIDOR.B3.COM.BR" in upper
        or "INVESTIDOR.B3.COM.BR" in upper
        or "EXTRATO DE MOVIMENTAÇÃO" in upper
        or "EXTRATO DE MOVIMENTACAO" in upper
        or "EXTRATO DE NEGOCIAÇÃO" in upper
        or "EXTRATO DE NEGOCIACAO" in upper
    )


def adapt_b3_rows_to_canonical(
    rows: list[list[str]],
    format_hint: str = "auto",
) -> B3AdaptResult:
    """Lógica central de parsing de linhas B3 (usada por CSV, XLSX e PDF)."""
    if not rows:
        return B3AdaptResult(
            success=False,
            format_detected="empty",
            errors=["Nenhuma linha com dados encontrada."],
        )

    # Localizar cabeçalho
    header_idx = 0
    headers_norm: list[str] = []
    for idx, r in enumerate(rows[:10]):
        norm = [_normalize_header_name(cell) for cell in r]
        if any("movimentacao" in h or "negocio" in h or "produto" in h or "entrada_saida" in h for h in norm):
            header_idx = idx
            headers_norm = norm
            break

    if not headers_norm:
        headers_norm = [_normalize_header_name(cell) for cell in rows[0]]

    # Identificar formato
    is_negociacao = any("negocio" in h for h in headers_norm) or (
        "codigo_de_negociacao" in headers_norm and any("preco" in h for h in headers_norm)
    )
    is_movimentacao = any("movimentacao" in h for h in headers_norm) or any(
        "entrada_saida" in h for h in headers_norm
    )

    if not is_negociacao and not is_movimentacao:
        if format_hint == "pdf_movimentacao":
            is_movimentacao = True
        else:
            return B3AdaptResult(
                success=False,
                format_detected="unknown",
                errors=["Formato não reconhecido como arquivo da Área do Investidor B3."],
            )

    format_name = "b3_negociacao_v1" if is_negociacao else "b3_movimentacao_v1"

    # Criar mapa de índices
    idx_map: dict[str, int] = {}
    for i, h in enumerate(headers_norm):
        if "data" in h:
            idx_map.setdefault("date", i)
        elif "codigo" in h or "ativo" in h or "ticker" in h or "produto" in h:
            idx_map.setdefault("ticker", i)
        elif "entrada_saida" in h:
            idx_map.setdefault("entry_exit", i)
        elif "tipo" in h or "movimentacao" in h or "operacao" in h:
            idx_map.setdefault("movement_type", i)
        elif "quantidade" in h or "qtd" in h:
            idx_map.setdefault("quantity", i)
        elif "preco" in h or "cotacao" in h:
            idx_map.setdefault("price", i)
        elif "valor" in h:
            idx_map.setdefault("total_value", i)
        elif "instituicao" in h or "corretora" in h:
            idx_map.setdefault("institution", i)

    canonical_rows: list[dict[str, Any]] = []
    skipped_items: list[B3SkippedItem] = []
    errors: list[str] = []
    seen_signatures: set[str] = set()

    for line_idx, row in enumerate(rows[header_idx + 1:], start=header_idx + 2):
        try:
            if not any(str(cell).strip() for cell in row):
                continue

            raw_date = str(row[idx_map["date"]]).strip() if "date" in idx_map and idx_map["date"] < len(row) else ""
            raw_ticker_cell = str(row[idx_map["ticker"]]).strip() if "ticker" in idx_map and idx_map["ticker"] < len(row) else ""
            raw_entry_exit = str(row[idx_map["entry_exit"]]).strip() if "entry_exit" in idx_map and idx_map["entry_exit"] < len(row) else ""
            raw_movement = str(row[idx_map["movement_type"]]).strip() if "movement_type" in idx_map and idx_map["movement_type"] < len(row) else ""
            raw_qty = str(row[idx_map["quantity"]]).strip() if "quantity" in idx_map and idx_map["quantity"] < len(row) else ""
            raw_price = str(row[idx_map["price"]]).strip() if "price" in idx_map and idx_map["price"] < len(row) else ""
            raw_total = str(row[idx_map["total_value"]]).strip() if "total_value" in idx_map and idx_map["total_value"] < len(row) else ""
            raw_inst = str(row[idx_map["institution"]]).strip() if "institution" in idx_map and idx_map["institution"] < len(row) else ""

            if not raw_date or not raw_ticker_cell:
                continue

            combined_op_text = f"{raw_entry_exit} {raw_movement}".upper()

            # 1. Segregação de eventos corporativos, proventos, empréstimos e transferências sem liquidação
            if any(kw in combined_op_text for kw in _CORPORATE_OR_INCOME_KEYWORDS):
                skipped_items.append(
                    B3SkippedItem(
                        line_number=line_idx,
                        raw_ticker=raw_ticker_cell,
                        movement_type=raw_movement or raw_entry_exit,
                        reason="Evento corporativo ou provento segregado do motor de transações.",
                    )
                )
                continue

            # 2. Segregação de direitos e recibos de subscrição (ex: SNAG12, MXRF12, ITSA2, etc.)
            ticker_clean = normalize_b3_ticker(raw_ticker_cell)
            if is_subscription_right_ticker(ticker_clean, raw_ticker_cell or combined_op_text):
                skipped_items.append(
                    B3SkippedItem(
                        line_number=line_idx,
                        raw_ticker=raw_ticker_cell,
                        movement_type=raw_movement or raw_entry_exit or "Subscrição",
                        reason="Direito ou recibo de subscrição segregado como evento corporativo.",
                    )
                )
                continue

            # Transferência pura sem liquidação de mercado (preço "-" ou sem valor)
            mov_upper = raw_movement.strip().upper()
            if ("TRANSFERÊNCIA" in mov_upper or "TRANSFERENCIA" in mov_upper) and "LIQUIDA" not in mov_upper:
                if raw_price.strip() == "-" or raw_total.strip() == "-" or not raw_price.strip():
                    skipped_items.append(
                        B3SkippedItem(
                            line_number=line_idx,
                            raw_ticker=raw_ticker_cell,
                            movement_type="Transferência",
                            reason="Transferência interna de custódia sem liquidação financeira de mercado.",
                        )
                    )
                    continue

            # Eventos corporativos de custódia (desdobro, bonificação, atualização de custódia, fração em ativos)
            is_custody_event = any(kw in combined_op_text for kw in _CUSTODY_EVENT_KEYWORDS)

            # 2. Mapeamento da operação (buy / sell)
            entry_upper = raw_entry_exit.strip().upper()

            if is_custody_event:
                if any(w in combined_op_text for w in ("DEBITO", "DÉBITO", "SAIDA", "SAÍDA", "SELL")):
                    operation = "sell"
                else:
                    operation = "buy"
            elif "APLICAÇÃO" in mov_upper or "APLICACAO" in mov_upper:
                operation = "buy"
            elif "RESGATE" in mov_upper:
                operation = "sell"
            elif "COMPRA" in mov_upper:
                operation = "buy"
            elif "VENDA" in mov_upper:
                operation = "sell"
            elif "TRANSFERÊNCIA - LIQUIDAÇÃO" in mov_upper or "TRANSFERENCIA - LIQUIDACAO" in mov_upper or "COMPRA / VENDA" in mov_upper:
                if any(w in entry_upper for w in ("CREDITO", "CRÉDITO", "ENTRADA", "BUY")):
                    operation = "buy"
                elif any(w in entry_upper for w in ("DEBITO", "DÉBITO", "SAIDA", "SAÍDA", "SELL")):
                    operation = "sell"
                else:
                    # Se não há coluna de Entrada/Saída explícita (ex: em alguns PDFs), assume compra padrão
                    operation = "buy"
            elif any(w in combined_op_text for w in ("CREDITO", "CRÉDITO", "ENTRADA", "BUY")):
                operation = "buy"
            elif any(w in combined_op_text for w in ("DEBITO", "DÉBITO", "SAIDA", "SAÍDA", "SELL")):
                operation = "sell"
            else:
                skipped_items.append(
                    B3SkippedItem(
                        line_number=line_idx,
                        raw_ticker=raw_ticker_cell,
                        movement_type=raw_movement or raw_entry_exit,
                        reason=f"Tipo de movimentação não operável: '{raw_movement or raw_entry_exit}'",
                    )
                )
                continue

            ticker = normalize_b3_ticker(raw_ticker_cell)
            if not ticker:
                continue

            date_str = parse_b3_date(raw_date)
            quantity = parse_b3_number(raw_qty)
            price = parse_b3_number(raw_price) if raw_price else Decimal("0")
            total_value = parse_b3_number(raw_total) if raw_total else Decimal("0")

            if quantity <= 0:
                continue

            if price <= 0 and total_value > 0:
                price = (total_value / quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            elif price <= 0:
                price = Decimal("0.01")  # Preço mínimo de proteção se ausente

            asset_type = infer_b3_asset_type(ticker, product_name=raw_ticker_cell)

            # Idempotência / Anti-duplicidade interna
            signature = f"{ticker}:{operation}:{date_str}:{quantity}:{price}"
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)

            if is_custody_event:
                notes = f"B3 Evento Corporativo: {raw_movement}"
            else:
                notes = f"B3 Área do Investidor ({raw_inst})" if raw_inst else "B3 Área do Investidor"

            canonical_rows.append({
                "ticker": ticker,
                "asset_type": asset_type,
                "operation": operation,
                "quantity": str(quantity),
                "price": str(price),
                "date": date_str,
                "fees": "0",
                "currency": "BRL",
                "notes": notes,
            })
        except Exception as exc:
            errors.append(f"Linha {line_idx}: falha ao processar ({exc})")

    # Segregar resgates de Renda Fixa (CDB, LCI, LCA, etc.) que não possuem aplicação no extrato
    # (contratos originados antes do período selecionado pelo investidor na Área do Investidor B3)
    rf_buys = {
        row["ticker"]
        for row in canonical_rows
        if row.get("asset_type") == AssetType.RENDA_FIXA.value and row.get("operation") == "buy"
    }

    filtered_canonical_rows: list[dict[str, Any]] = []
    for item in canonical_rows:
        if (
            item.get("asset_type") == AssetType.RENDA_FIXA.value
            and item.get("operation") == "sell"
            and item.get("ticker") not in rf_buys
        ):
            skipped_items.append(
                B3SkippedItem(
                    line_number=0,
                    raw_ticker=item.get("ticker", ""),
                    movement_type="Resgate de Renda Fixa",
                    reason="Resgate de Renda Fixa sem aplicação correspondente no período do extrato (contrato originado antes do período selecionado).",
                )
            )
        else:
            filtered_canonical_rows.append(item)

    canonical_rows = filtered_canonical_rows

    # Ordenar transações em ordem cronológica (data ASC, compras antes de vendas na mesma data)
    # Extratos da B3 vêm em ordem decrescente (mais recente para o mais antigo);
    # ordenar cronologicamente garante que o histórico de compras preceda as vendas.
    canonical_rows.sort(
        key=lambda r: (
            r.get("date", ""),
            0 if r.get("operation") == "buy" else 1,
        )
    )

    # Segregar ou calibrar débitos de eventos corporativos de custódia (ex: Fração em Ativos)
    # Se o investidor não possui saldo em custódia desse ativo no período do extrato (ex: frações
    # oriundas de desmembramento ou bonificação de Units posteriormente leiloadas como KLBN3),
    # o débito é segregado como informativo para não gerar vendas descobertas artificiais.
    running_balances: dict[str, float] = {}
    adjusted_canonical_rows: list[dict[str, Any]] = []

    for item in canonical_rows:
        ticker = item.get("ticker", "")
        op = item.get("operation", "")
        qty = float(item.get("quantity") or 0.0)
        is_custody = "Evento Corporativo" in item.get("notes", "")

        if op == "buy":
            running_balances[ticker] = running_balances.get(ticker, 0.0) + qty
            adjusted_canonical_rows.append(item)
        elif op == "sell":
            avail = running_balances.get(ticker, 0.0)
            if is_custody:
                if avail <= 1e-7:
                    skipped_items.append(
                        B3SkippedItem(
                            line_number=0,
                            raw_ticker=ticker,
                            movement_type="Fração em Ativos",
                            reason="Fração ou ajuste de custódia sem saldo disponível no período do extrato segregado.",
                        )
                    )
                    continue
                elif qty > avail and not math.isclose(qty, avail, rel_tol=1e-7, abs_tol=1e-7):
                    item["quantity"] = str(round(avail, 4))
                    running_balances[ticker] = 0.0
                    adjusted_canonical_rows.append(item)
                else:
                    running_balances[ticker] = max(0.0, avail - qty)
                    adjusted_canonical_rows.append(item)
            else:
                running_balances[ticker] = max(0.0, avail - qty)
                adjusted_canonical_rows.append(item)

    canonical_rows = adjusted_canonical_rows

    # Gerar CSV canônico
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=["ticker", "asset_type", "operation", "quantity", "price", "date", "fees", "currency", "notes"],
    )
    writer.writeheader()
    for item in canonical_rows:
        writer.writerow(item)

    return B3AdaptResult(
        success=len(errors) == 0 and len(canonical_rows) > 0,
        format_detected=format_name,
        canonical_rows=canonical_rows,
        canonical_csv=output.getvalue(),
        skipped_items=skipped_items,
        errors=errors,
    )


def adapt_b3_investor_csv_to_canonical(raw_content: str | bytes) -> B3AdaptResult:
    """Converte o conteúdo CSV da Área do Investidor B3 no DTO canônico de importação."""
    if isinstance(raw_content, bytes):
        try:
            raw_content = raw_content.decode('utf-8')
        except UnicodeDecodeError:
            raw_content = raw_content.decode('latin-1', errors='replace')

    if not raw_content or not raw_content.strip():
        return B3AdaptResult(
            success=False,
            format_detected="empty",
            errors=["Conteúdo vazio ou inválido."],
        )

    delimiter = _detect_delimiter(raw_content)
    stream = io.StringIO(raw_content.strip())
    reader = csv.reader(stream, delimiter=delimiter)

    rows = [r for r in reader if any(cell.strip() for cell in r)]
    return adapt_b3_rows_to_canonical(rows)


def adapt_b3_investor_xlsx_to_canonical(xlsx_bytes: bytes) -> B3AdaptResult:
    """Converte arquivo Excel (.xlsx) da Área do Investidor B3 em transações canônicas."""
    if not openpyxl:
        return B3AdaptResult(
            success=False,
            format_detected="b3_xlsx",
            errors=["Biblioteca openpyxl não instalada no ambiente."],
        )

    try:
        wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), data_only=True)
    except Exception as exc:
        return B3AdaptResult(
            success=False,
            format_detected="b3_xlsx",
            errors=[f"Falha ao abrir planilha Excel: {exc}"],
        )

    # Escolher a melhor aba: 'Movimentação', 'Negociação', ou ativa
    sheet = None
    for name in wb.sheetnames:
        norm_name = _normalize_header_name(name)
        if "movimentacao" in norm_name or "negociacao" in norm_name:
            sheet = wb[name]
            break
    if sheet is None:
        sheet = wb.active

    if sheet is None:
        return B3AdaptResult(
            success=False,
            format_detected="b3_xlsx",
            errors=["A planilha não contém abas utilizáveis."],
        )

    raw_rows: list[list[str]] = []
    for row in sheet.iter_rows(values_only=True):
        raw_rows.append([str(c) if c is not None else "" for c in row])

    res = adapt_b3_rows_to_canonical(raw_rows)
    if res.format_detected == "b3_movimentacao_v1":
        res.format_detected = "b3_movimentacao_xlsx_v1"
    return res


def adapt_b3_investor_pdf_to_canonical(pdf_bytes: bytes) -> B3AdaptResult:
    """Converte arquivo PDF da Área do Investidor B3 em transações canônicas.

    Lida de forma resiliente com entradas de movimentação quebradas em múltiplas linhas
    de texto (razão social e instituição longas).
    """
    if not pypdf:
        return B3AdaptResult(
            success=False,
            format_detected="b3_pdf",
            errors=["Biblioteca pypdf não instalada no ambiente."],
        )

    try:
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    except Exception as exc:
        return B3AdaptResult(
            success=False,
            format_detected="b3_pdf",
            errors=[f"Falha ao ler PDF da B3: {exc}"],
        )

    pages_text: list[str] = []
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            pages_text.append(extracted)

    full_text = "\n".join(pages_text)
    if not full_text.strip():
        return B3AdaptResult(
            success=False,
            format_detected="b3_pdf_empty",
            errors=["PDF da B3 sem texto legível."],
        )

    lines = full_text.splitlines()
    current_date = ""

    # Linha com dados termina em: <Quantidade> R$ <Preço> R$ <Valor>
    row_tail_pattern = re.compile(
        r"([\d.,]+)\s+(?:R\$\s*)?([\d.,-]+)\s+(?:R\$\s*)?([\d.,-]+)\s*$",
        re.IGNORECASE,
    )

    known_moves = [
        ("APLICAÇÃO", "Credito", "APLICAÇÃO"),
        ("APLICACAO", "Credito", "APLICAÇÃO"),
        ("RESGATE ANTECIPADO/", "Debito", "RESGATE ANTECIPADO/"),
        ("RESGATE ANTECIPADO", "Debito", "RESGATE ANTECIPADO"),
        ("RESGATE", "Debito", "RESGATE"),
        ("COMPRA / VENDA", "Credito", "COMPRA / VENDA"),
        ("Compra", "Credito", "Compra"),
        ("Venda", "Debito", "Venda"),
        ("Dividendo", "Credito", "Dividendo"),
        ("Juros Sobre Capital Próprio", "Credito", "Juros Sobre Capital Próprio"),
        ("Juros Sobre Capital Proprio", "Credito", "Juros Sobre Capital Próprio"),
        ("Rendimento", "Credito", "Rendimento"),
        ("Reembolso", "Credito", "Reembolso"),
        ("Empréstimo", "Credito", "Empréstimo"),
        ("Emprestimo", "Credito", "Empréstimo"),
        ("Transferência - Liquidação", "Credito", "Transferência - Liquidação"),
        ("Transferencia - Liquidacao", "Credito", "Transferência - Liquidação"),
        ("Transferência", "Credito", "Transferência"),
        ("Transferencia", "Credito", "Transferência"),
        ("Fração em Ativos", "Debito", "Fração em Ativos"),
        ("Fracao em Ativos", "Debito", "Fração em Ativos"),
        ("Grupamento", "Credito", "Grupamento"),
        ("Leilão de Fração", "Credito", "Leilão de Fração"),
        ("Leilao de Fracao", "Credito", "Leilão de Fração"),
        ("Direitos de Subscrição - Não Exercido", "Debito", "Direitos de Subscrição - Não Exercido"),
        ("Direitos de Subscrição", "Credito", "Direitos de Subscrição"),
        ("Direito de Subscrição", "Credito", "Direito de Subscrição"),
        ("Cessão de Direitos - Solicitada", "Debito", "Cessão de Direitos - Solicitada"),
        ("Cessão de Direitos", "Credito", "Cessão de Direitos"),
        ("Atualização", "Credito", "Atualização"),
        ("Desdobro", "Credito", "Desdobro"),
        ("Bonificação em Ativos", "Credito", "Bonificação em Ativos"),
        ("Resgate de Cotas", "Debito", "Resgate de Cotas"),
    ]
    known_moves.sort(key=lambda x: len(x[0]), reverse=True)

    tabular_rows: list[list[str]] = [
        ["Entrada/Saída", "Data", "Movimentação", "Produto", "Instituição", "Quantidade", "Preço unitário", "Valor da Operação"]
    ]

    buffer_lines: list[str] = []
    noise_tokens = (
        "acesse investidor",
        "extrato de movimenta",
        "filtros aplicados",
        "data inicial",
        "tipo de invest",
        "tipo de movimenta",
        "institui",
        "cpf/cnpj",
    )

    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue

        # Verifica se é cabeçalho de data
        date_match = _B3_PDF_DATE_SECTION_PATTERN.match(line_clean)
        if date_match:
            day, month_str, year = date_match.groups()
            m_num = MONTHS_PT.get(month_str.lower(), 1)
            current_date = f"{year}-{m_num:02d}-{int(day):02d}"
            buffer_lines = []
            continue

        lower_line = line_clean.lower()
        # Excluir cabeçalhos de tabela B3 (inteiros ou quebrados em linhas consecutivas)
        if (
            ("movimenta" in lower_line and "produto" in lower_line)
            or ("preço unit" in lower_line or "preco unit" in lower_line)
            or ("valor da opera" in lower_line)
            or any(token in lower_line for token in noise_tokens)
        ):
            continue

        buffer_lines.append(line_clean)
        if row_tail_pattern.search(line_clean) and current_date:
            combined_text = " ".join(buffer_lines)
            comb_tail_match = row_tail_pattern.search(combined_text)
            if not comb_tail_match:
                buffer_lines = []
                continue

            qty_str, price_str, val_str = comb_tail_match.groups()
            head_str = combined_text[:comb_tail_match.start()].strip()
            buffer_lines = []

            entry_exit = "Credito"
            mov = "Transferência - Liquidação"
            prod_and_inst = head_str

            for cd_prefix, cd_val in [
                ("CREDITO ", "Credito"),
                ("CRÉDITO ", "Credito"),
                ("DEBITO ", "Debito"),
                ("DÉBITO ", "Debito"),
            ]:
                if head_str.upper().startswith(cd_prefix):
                    entry_exit = cd_val
                    head_str = head_str[len(cd_prefix):].strip()
                    break

            for prefix, default_ee, norm_mov in known_moves:
                if head_str.upper().startswith(prefix.upper()):
                    entry_exit = default_ee
                    mov = norm_mov
                    prod_and_inst = head_str[len(prefix):].strip()
                    break

            tabular_rows.append([
                entry_exit,
                current_date,
                mov,
                prod_and_inst,
                "",
                qty_str,
                price_str,
                val_str,
            ])

    result = adapt_b3_rows_to_canonical(tabular_rows, format_hint="pdf_movimentacao")
    result.format_detected = "b3_movimentacao_pdf_v1"
    return result
