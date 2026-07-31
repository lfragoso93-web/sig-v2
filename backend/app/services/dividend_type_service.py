"""Normalização canônica e sem dependências externas dos tipos de provento."""

import unicodedata

from app.models.dividend_enums import DividendType

CASH_DIVIDEND_TYPES = frozenset(
    {
        DividendType.DIVIDENDO,
        DividendType.JCP,
        DividendType.RENDIMENTO,
        DividendType.AMORTIZACAO,
        DividendType.OUTROS,
    }
)


def _normalized_label(value: str | None) -> str:
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", str(value))
    without_accents = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    clean = without_accents.upper().strip()
    return " ".join(clean.replace("_", " ").replace("-", " ").split())


def normalize_dividend_type(
    raw: str | DividendType | None,
    category: str | None = None,
) -> DividendType:
    """Normaliza enums, valores legados e rótulos recebidos de provedores."""
    if isinstance(raw, DividendType):
        return raw
    label = _normalized_label(raw)
    normalized_category = _normalized_label(category)
    if "SUBSCR" in label or "SUBSCR" in normalized_category:
        return DividendType.SUBSCRICAO
    if (
        "BONIFIC" in label
        or "BONIFIC" in normalized_category
        or "STOCK" in normalized_category
    ):
        return DividendType.BONIFICACAO
    if "JCP" in label or "JUROS SOBRE CAPITAL" in label:
        return DividendType.JCP
    if "AMORT" in label:
        return DividendType.AMORTIZACAO
    if "REND" in label or "FII" in normalized_category:
        return DividendType.RENDIMENTO
    if "DIVID" in label:
        return DividendType.DIVIDENDO
    if label in {item.value for item in DividendType}:
        return DividendType(label)
    return DividendType.OUTROS
