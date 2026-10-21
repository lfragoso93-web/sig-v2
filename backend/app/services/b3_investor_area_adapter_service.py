"""Adapter para arquivos exportados pela Área do Investidor B3.

Converte arquivos de negociação e movimentação da B3 no formato/DTO canônico
de importação do SGI v2 sem acoplamento direto com persistência no banco.

Arquitetura obrigatória (Issue #358):
    arquivo B3 -> parser/adapter B3 -> DTO canônico de import -> validação/dry-run -> TransactionWriteService -> rebuild canônico
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from app.models.asset import AssetType

_ODD_LOT_PATTERN = re.compile(r"^([A-Z]{4}\d{1,2})F$")
_B3_DATE_PATTERN = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
_TICKER_EXTRACT_PATTERN = re.compile(r"\b([A-Z]{4}\d{1,2}(?:F)?)\b")

# Eventos de proventos/ações corporativas que não devem gerar compras/vendas artificiais
_CORPORATE_OR_INCOME_KEYWORDS = {
    "DIVIDENDO",
    "JUROS SOBRE CAPITAL PROPRIO",
    "JUROS SOBRE CAPITAL PRÓPRIO",
    "JSCP",
    "JCP",
    "RENDIMENTO",
    "BONIFICACAO",
    "BONIFICAÇÃO",
    "FRACAO",
    "FRAÇÃO",
    "ATUALIZACAO",
    "ATUALIZAÇÃO",
    "DIREITO DE SUBSCRICAO",
    "DIREITO DE SUBSCRIÇÃO",
    "RECIBO DE SUBSCRICAO",
    "RECIBO DE SUBSCRIÇÃO",
    "AMORTIZACAO",
    "AMORTIZAÇÃO",
    "LEILAO DE FRACOES",
    "LEILÃO DE FRAÇÕES",
}


@dataclass
class B3SkippedItem:
    line_number: int
    raw_ticker: str
    movement_type: str
    reason: str

    def to_dict(self) -> dict:
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
    canonical_rows: list[dict] = field(default_factory=list)
    canonical_csv: str = ""
    skipped_items: list[B3SkippedItem] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def normalize_b3_ticker(raw_ticker: str) -> str:
    """Normaliza o ticker removendo razão social e sufixo fracionário 'F'."""
    cleaned = raw_ticker.strip().upper()
    if not cleaned:
        return ""

    if cleaned.startswith("TESOURO"):
        # Normalizar títulos do Tesouro Direto: "TESOURO SELIC 2029 - ..." -> "TESOURO SELIC 2029"
        return cleaned.split("-")[0].strip()

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


def infer_b3_asset_type(ticker: str) -> str:
    """Infere o tipo de ativo inicial com base no padrão do ticker."""
    t = ticker.upper()
    if t.startswith("TESOURO"):
        return AssetType.TESOURO_DIRETO.value
    if t.endswith(("34", "35")):
        return AssetType.BDR.value
    if t.endswith("11"):
        return AssetType.FII.value
    if any(t.endswith(s) for s in ("3", "4", "5", "6")):
        return AssetType.ACAO.value
    return AssetType.OUTRO.value


def parse_b3_number(raw_value: str) -> Decimal:
    """Converte valores numéricos no padrão brasileiro ('1.234,56' ou '35,50') para Decimal."""
    v = raw_value.strip().replace("R$", "").replace(" ", "")
    if not v or v == "-":
        return Decimal("0")
    if "," in v:
        v = v.replace(".", "").replace(",", ".")
    try:
        return Decimal(v)
    except InvalidOperation:
        return Decimal("0")


def parse_b3_date(raw_date: str) -> str:
    """Converte 'DD/MM/YYYY' para 'YYYY-MM-DD'."""
    raw = raw_date.strip()
    match = _B3_DATE_PATTERN.match(raw)
    if match:
        day, month, year = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
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
    h = header.strip().lower()
    h = h.replace("á", "a").replace("ã", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ç", "c")
    return re.sub(r"[^a-z0-9_]", "", h.replace(" ", "_").replace("/", "_"))


def is_b3_csv_content(raw_content: str) -> bool:
    """Detecta rapidamente se o cabeçalho do arquivo corresponde à Área do Investidor B3."""
    if not raw_content or not raw_content.strip():
        return False
    first_lines = raw_content.strip().splitlines()[:5]
    for line in first_lines:
        line_norm = _normalize_header_name(line)
        if any(token in line_norm for token in (
            "negocio",
            "codigo_de_negociacao",
            "entrada_saida",
            "movimentacao",
        )):
            return True
    return False


def adapt_b3_investor_csv_to_canonical(raw_content: str) -> B3AdaptResult:
    """Converte o conteúdo CSV da Área do Investidor B3 no DTO canônico de importação."""
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
    if not rows:
        return B3AdaptResult(
            success=False,
            format_detected="empty",
            errors=["Nenhuma linha com dados encontrada."],
        )

    header_row = rows[0]
    headers_norm = [_normalize_header_name(h) for h in header_row]

    # Identificar formato
    is_negociacao = any("negocio" in h for h in headers_norm) or (
        "codigo_de_negociacao" in headers_norm and any("preco" in h for h in headers_norm)
    )
    is_movimentacao = any("movimentacao" in h for h in headers_norm) or any(
        "entrada_saida" in h for h in headers_norm
    )

    if not is_negociacao and not is_movimentacao:
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

    canonical_rows: list[dict] = []
    skipped_items: list[B3SkippedItem] = []
    errors: list[str] = []
    seen_signatures: set[str] = set()

    for line_idx, row in enumerate(rows[1:], start=2):
        try:
            raw_date = row[idx_map["date"]].strip() if "date" in idx_map and idx_map["date"] < len(row) else ""
            raw_ticker_cell = row[idx_map["ticker"]].strip() if "ticker" in idx_map and idx_map["ticker"] < len(row) else ""
            raw_entry_exit = row[idx_map["entry_exit"]].strip() if "entry_exit" in idx_map and idx_map["entry_exit"] < len(row) else ""
            raw_movement = row[idx_map["movement_type"]].strip() if "movement_type" in idx_map and idx_map["movement_type"] < len(row) else ""
            raw_qty = row[idx_map["quantity"]].strip() if "quantity" in idx_map and idx_map["quantity"] < len(row) else ""
            raw_price = row[idx_map["price"]].strip() if "price" in idx_map and idx_map["price"] < len(row) else ""
            raw_total = row[idx_map["total_value"]].strip() if "total_value" in idx_map and idx_map["total_value"] < len(row) else ""
            raw_inst = row[idx_map["institution"]].strip() if "institution" in idx_map and idx_map["institution"] < len(row) else ""

            if not raw_date or not raw_ticker_cell:
                continue

            combined_op_text = f"{raw_entry_exit} {raw_movement}".upper()

            # 1. Segregação de eventos corporativos e proventos
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

            # 2. Mapeamento da operação (buy / sell)
            if any(w in combined_op_text for w in ("COMPRA", "CREDITO", "CRÉDITO", "ENTRADA", "BUY")):
                operation = "buy"
            elif any(w in combined_op_text for w in ("VENDA", "DEBITO", "DÉBITO", "SAIDA", "SAÍDA", "SELL")):
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

            asset_type = infer_b3_asset_type(ticker)

            # Idempotência / Anti-duplicidade interna
            signature = f"{ticker}:{operation}:{date_str}:{quantity}:{price}"
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)

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

    # Gerar CSV canônico
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=["ticker", "asset_type", "operation", "quantity", "price", "date", "fees", "currency", "notes"])
    writer.writeheader()
    for item in canonical_rows:
        writer.writerow(item)

    return B3AdaptResult(
        success=len(errors) == 0,
        format_detected=format_name,
        canonical_rows=canonical_rows,
        canonical_csv=output.getvalue(),
        skipped_items=skipped_items,
        errors=errors,
    )
