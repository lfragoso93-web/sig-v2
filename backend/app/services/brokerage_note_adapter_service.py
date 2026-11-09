"""Adapter para Notas de Corretagem dos Bancos e Corretoras (Padrão Sinacor e variantes).

Converte notas de corretagem (PDF ou texto/CSV) emitidas por instituições financeiras
brasileiras (Banco Inter, XP Investimentos, Clear, Rico, BTG Pactual, NuInvest, Itaú,
Bradesco/Ágora, Santander, Genial, etc.) no formato canônico de importação do SGI v2.

Arquitetura obrigatória:
    Nota de Corretagem (PDF/texto) -> parser/adapter -> DTO canônico -> dry-run -> TransactionWriteService -> rebuild canônico
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from app.models.asset import AssetType
from app.services.b3_investor_area_adapter_service import (
    infer_b3_asset_type,
    normalize_b3_ticker,
    parse_b3_date,
    parse_b3_number,
)

try:
    import pypdf
except ImportError:
    pypdf = None  # type: ignore[assignment]


_ODD_LOT_PATTERN = re.compile(r"^([A-Z]{4}\d{1,2})F$")
_TICKER_EXTRACT_PATTERN = re.compile(r"\b([A-Z]{4}\d{1,2}[A-Z]?)\b")

# Padrão da linha de negócio Sinacor:
# [1-BOVESPA|BOVESPA] [C|V] [VISTA|FRACIONARIO|OPCAO|TERMO] <ESPECIFICAÇÃO> <QUANTIDADE> <PREÇO> <VALOR TOTAL> [D|C]
_SINACOR_TRADE_LINE_PATTERN = re.compile(
    r"^\s*(?:1-BOVESPA|BOVESPA|2-BOLSA|BOLSA)?\s*([CV])\s+"
    r"(?:VISTA|FRACIONARIO|FRACIONÁRIO|OPCAO|OPÇÃO|TERMO|EXERC\s+OPCAO)?\s*"
    r"(.*?)\s+"
    r"([\d.,]+)\s+"
    r"([\d.,]+)\s+"
    r"([\d.,]+)\s*"
    r"([DC])?\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# Identificação de cabeçalho de Nota de Corretagem
_NOTE_HEADER_KEYWORDS = (
    "NOTA DE CORRETAGEM",
    "NOTA DE NEGOCIACAO",
    "NOTA DE NEGOCIAÇÃO",
    "NR. NOTA",
    "NR NOTA",
    "NUMERO DA NOTA",
    "NÚMERO DA NOTA",
    "DATA PREGÃO",
    "DATA PREGAO",
    "DATA DO PREGÃO",
    "DATA DO PREGAO",
)

# Identificação de Corretoras / Bancos comuns
_KNOWN_BROKERS = (
    ("INTER", "Banco Inter / Inter DTVM"),
    ("XP INVESTIMENTOS", "XP Investimentos"),
    ("CLEAR", "Clear Corretora"),
    ("RICO", "Rico Investimentos"),
    ("BTG PACTUAL", "BTG Pactual"),
    ("NU INVEST", "NuInvest"),
    ("NUBANK", "NuInvest / Nubank"),
    ("ITAU", "Itaú Corretora"),
    ("ITAÚ", "Itaú Corretora"),
    ("BRADESCO", "Bradesco / Ágora"),
    ("AGORA", "Ágora Investimentos"),
    ("ÁGORA", "Ágora Investimentos"),
    ("SANTANDER", "Santander Corretora"),
    ("GENIAL", "Genial Investimentos"),
    ("ORAMA", "Órama Investimentos"),
    ("ÓRAMA", "Órama Investimentos"),
    ("SAFRA", "Safra Corretora"),
    ("TORO", "Toro Investimentos"),
    ("MODAL", "ModalMais"),
)


@dataclass
class BrokerageSkippedItem:
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
class BrokerageNoteAdaptResult:
    success: bool
    format_detected: str
    canonical_rows: list[dict[str, Any]] = field(default_factory=list)
    canonical_csv: str = ""
    skipped_items: list[BrokerageSkippedItem] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    note_date: str = ""
    broker_name: str = ""
    note_number: str = ""
    total_fees: Decimal = Decimal("0")


def is_brokerage_note_content(raw_text: str) -> bool:
    """Verifica se o conteúdo textual corresponde a uma nota de corretagem padrão Sinacor."""
    if not raw_text or not raw_text.strip():
        return False
    upper = raw_text.upper()
    has_note_keyword = any(kw in upper for kw in _NOTE_HEADER_KEYWORDS)
    has_bovespa_or_cv = (
        ("1-BOVESPA" in upper or "BOVESPA" in upper or "BOLSA" in upper)
        and ("VISTA" in upper or "FRACIONARIO" in upper or "FRACIONÁRIO" in upper or "C/V" in upper)
    )
    has_date_pregao = "PREGÃO" in upper or "PREGAO" in upper or "DATA OPERAÇÃO" in upper
    return (has_note_keyword and (has_bovespa_or_cv or has_date_pregao)) or (
        has_bovespa_or_cv and has_date_pregao
    )


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extrai texto completo de todas as páginas de um PDF usando pypdf."""
    if not pypdf:
        raise RuntimeError("Biblioteca pypdf não instalada para leitura de PDFs.")
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    pages_text: list[str] = []
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            pages_text.append(extracted)
    return "\n".join(pages_text)


def _detect_broker(text: str) -> str:
    upper = text.upper()
    for token, name in _KNOWN_BROKERS:
        if token in upper:
            return name
    return "Corretora"


def _extract_note_date(text: str) -> str:
    """Extrai a data do pregão/operação da nota e retorna no formato YYYY-MM-DD."""
    patterns = [
        re.compile(r"Data\s+(?:do\s+)?preg[aã]o:?\s*(\d{1,2}/\d{1,2}/\d{4})", re.IGNORECASE),
        re.compile(r"Data\s+opera[çc][aã]o:?\s*(\d{1,2}/\d{1,2}/\d{4})", re.IGNORECASE),
        re.compile(r"Data\s+neg[oó]cio:?\s*(\d{1,2}/\d{1,2}/\d{4})", re.IGNORECASE),
        re.compile(r"Data:?\s*(\d{1,2}/\d{1,2}/\d{4})", re.IGNORECASE),
    ]
    for pat in patterns:
        m = pat.search(text)
        if m:
            try:
                return parse_b3_date(m.group(1))
            except ValueError:
                continue
    return ""


def _extract_note_number(text: str) -> str:
    """Extrai o número da nota de corretagem."""
    patterns = [
        re.compile(r"Nr\.?\s*nota:?\s*(\d+)", re.IGNORECASE),
        re.compile(r"N[uú]mero\s+(?:da\s+)?nota:?\s*(\d+)", re.IGNORECASE),
        re.compile(r"Nota\s+n[ºo°]?\s*:?\s*(\d+)", re.IGNORECASE),
    ]
    for pat in patterns:
        m = pat.search(text)
        if m:
            return m.group(1).strip()
    return ""


def _extract_fees(text: str) -> Decimal:
    """Extrai taxas e custos operacionais da nota de corretagem Sinacor."""
    total_fees = Decimal("0")

    # Padrão Sinacor: "Taxa de liquidação: R$ X,XX" ou "Total de despesas: R$ X,XX"
    # Primeiro verifica se há "Total custos / despesas" consolidado
    consolidated_match = re.search(
        r"Total\s+(?:de\s+)?(?:custos\s*(?:[/e]\s*)?despesas|custos|despesas):?\s*(?:R\$\s*)?([\d.,]+)",
        text,
        re.IGNORECASE,
    )
    if consolidated_match:
        val = parse_b3_number(consolidated_match.group(1))
        if val > 0:
            return val

    # Caso contrário, soma os itens individuais conhecidos
    individual_patterns = [
        re.compile(r"Taxa\s+de\s+liquida[çc][aã]o:?\s*(?:R\$\s*)?([\d.,]+)", re.IGNORECASE),
        re.compile(r"Taxa\s+de\s+registro:?\s*(?:R\$\s*)?([\d.,]+)", re.IGNORECASE),
        re.compile(r"Emolumentos:?\s*(?:R\$\s*)?([\d.,]+)", re.IGNORECASE),
        re.compile(r"Taxa\s+(?:de\s+)?cust[oó]dia:?\s*(?:R\$\s*)?([\d.,]+)", re.IGNORECASE),
        re.compile(r"Taxa\s+operacional:?\s*(?:R\$\s*)?([\d.,]+)", re.IGNORECASE),
        re.compile(r"Corretagem:?\s*(?:R\$\s*)?([\d.,]+)", re.IGNORECASE),
        re.compile(r"ISS\s*(?:\([^)]*\))?:?\s*(?:R\$\s*)?([\d.,]+)", re.IGNORECASE),
    ]
    for pat in individual_patterns:
        m = pat.search(text)
        if m:
            total_fees += parse_b3_number(m.group(1))

    return total_fees


def adapt_brokerage_note_to_canonical(raw_input: str | bytes) -> BrokerageNoteAdaptResult:
    """Processa nota de corretagem (PDF ou texto) e converte para transações canônicas."""
    if isinstance(raw_input, bytes):
        if raw_input.startswith(b"%PDF"):
            try:
                text = extract_text_from_pdf(raw_input)
            except Exception as exc:
                return BrokerageNoteAdaptResult(
                    success=False,
                    format_detected="brokerage_note_pdf",
                    errors=[f"Falha ao ler PDF da nota de corretagem: {exc}"],
                )
        else:
            for enc in ("utf-8-sig", "utf-8", "latin-1"):
                try:
                    text = raw_input.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                return BrokerageNoteAdaptResult(
                    success=False,
                    format_detected="unknown",
                    errors=["Não foi possível identificar a codificação do arquivo."],
                )
    else:
        text = raw_input

    if not text or not text.strip():
        return BrokerageNoteAdaptResult(
            success=False,
            format_detected="empty",
            errors=["Nota de corretagem vazia."],
        )

    note_date = _extract_note_date(text)
    broker_name = _detect_broker(text)
    note_number = _extract_note_number(text)
    total_fees = _extract_fees(text)

    canonical_rows: list[dict[str, Any]] = []
    skipped_items: list[BrokerageSkippedItem] = []
    errors: list[str] = []

    # Localizar linhas de negociação Sinacor
    matches = list(_SINACOR_TRADE_LINE_PATTERN.finditer(text))

    if not matches:
        # Tentar parsing linha a linha alternativo se regex tabular estrito falhar
        for idx, line in enumerate(text.splitlines(), start=1):
            line_str = line.strip()
            if not line_str:
                continue
            # Linhas que parecem negócio: "C" ou "V", ticker de 4-6 chars, quantidade e preço
            alt_m = re.match(
                r"^([CV])\s+(?:VISTA|FRACION[AÁ]RIO)?\s*(.*?)\s+([\d.,]+)\s+([\d.,]+)(?:\s+([\d.,]+))?",
                line_str,
                re.IGNORECASE,
            )
            if alt_m:
                matches.append(alt_m)

    if not matches:
        return BrokerageNoteAdaptResult(
            success=False,
            format_detected="brokerage_note_unknown",
            errors=["Nenhuma operação de compra/venda identificada na nota de corretagem."],
        )

    # Coletar dados preliminares das operações para rateio proporcional de taxas
    parsed_trades: list[dict[str, Any]] = []
    total_volume = Decimal("0")

    for idx, m in enumerate(matches, start=1):
        try:
            cv = m.group(1).upper()
            spec = m.group(2).strip()
            qty_str = m.group(3).strip()
            price_str = m.group(4).strip()
            total_str = m.group(5).strip() if len(m.groups()) >= 5 and m.group(5) else ""

            # Extrair ticker da especificação
            ticker_match = _TICKER_EXTRACT_PATTERN.search(spec)
            if ticker_match:
                ticker = normalize_b3_ticker(ticker_match.group(1))
            else:
                ticker = normalize_b3_ticker(spec.split()[0] if spec else "")

            if not ticker or len(ticker) < 4:
                skipped_items.append(
                    BrokerageSkippedItem(
                        line_number=idx,
                        raw_ticker=spec,
                        movement_type=f"Operação {cv}",
                        reason=f"Não foi possível extrair um ticker válido da especificação: '{spec}'",
                    )
                )
                continue

            quantity = parse_b3_number(qty_str)
            price = parse_b3_number(price_str)
            trade_total = parse_b3_number(total_str) if total_str else (quantity * price)

            if quantity <= 0 or price <= 0:
                continue

            operation = "buy" if cv == "C" else "sell"
            asset_type = infer_b3_asset_type(ticker)

            parsed_trades.append({
                "ticker": ticker,
                "asset_type": asset_type,
                "operation": operation,
                "quantity": quantity,
                "price": price,
                "total_value": trade_total,
                "spec": spec,
                "line_idx": idx,
            })
            total_volume += trade_total
        except Exception as exc:
            errors.append(f"Operação {idx}: falha ao processar ({exc})")

    # Ratear taxas proporcionalmente ao volume de cada operação
    for trade in parsed_trades:
        if total_fees > 0 and total_volume > 0:
            trade_fee = (total_fees * (trade["total_value"] / total_volume)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            trade_fee = Decimal("0.00")

        trade_date = note_date or parse_b3_date("01/01/2026")
        note_ref = f"Nota {note_number}" if note_number else "Nota de Corretagem"
        notes = f"{broker_name} - {note_ref}"

        canonical_rows.append({
            "ticker": trade["ticker"],
            "asset_type": trade["asset_type"],
            "operation": trade["operation"],
            "quantity": str(trade["quantity"]),
            "price": str(trade["price"]),
            "date": trade_date,
            "fees": str(trade_fee),
            "currency": "BRL",
            "notes": notes,
        })

    # Gerar CSV canônico
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=["ticker", "asset_type", "operation", "quantity", "price", "date", "fees", "currency", "notes"],
    )
    writer.writeheader()
    for item in canonical_rows:
        writer.writerow(item)

    return BrokerageNoteAdaptResult(
        success=len(errors) == 0 and len(canonical_rows) > 0,
        format_detected="sinacor_brokerage_note_v1",
        canonical_rows=canonical_rows,
        canonical_csv=output.getvalue(),
        skipped_items=skipped_items,
        errors=errors,
        note_date=note_date,
        broker_name=broker_name,
        note_number=note_number,
        total_fees=total_fees,
    )


def adapt_brokerage_note_text_to_canonical(text: str) -> BrokerageNoteAdaptResult:
    """Atalho para adaptar notas de corretagem em formato de texto."""
    return adapt_brokerage_note_to_canonical(text)


def adapt_brokerage_note_pdf_to_canonical(pdf_bytes: bytes) -> BrokerageNoteAdaptResult:
    """Atalho para adaptar notas de corretagem em formato binário PDF."""
    return adapt_brokerage_note_to_canonical(pdf_bytes)
