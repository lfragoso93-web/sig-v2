"""Políticas fiscais explícitas por classe para a apuração mensal do IRPF.

O catálogo não calcula posição, custo ou resultado realizado. Ele apenas resolve
semântica fiscal e será consumido gradualmente pelo motor mensal da Issue #56.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class TaxAssessmentGroup(StrEnum):
    """Grupos que podem compartilhar base e prejuízo na mesma modalidade."""

    STOCKS = "stocks"
    BDR = "bdr"
    ETF = "etf"
    REAL_ESTATE_FUNDS = "real_estate_funds"


@dataclass(frozen=True)
class TaxClassPolicy:
    """Contrato fiscal mínimo por classe de ativo negociado em bolsa."""

    canonical_class: str
    common_group: TaxAssessmentGroup
    day_trade_group: TaxAssessmentGroup
    common_rate: Decimal
    day_trade_rate: Decimal
    monthly_exemption_limit: Decimal | None

    @property
    def has_monthly_exemption(self) -> bool:
        return self.monthly_exemption_limit is not None


_POLICIES: dict[str, TaxClassPolicy] = {
    "ACAO": TaxClassPolicy(
        canonical_class="ACAO",
        common_group=TaxAssessmentGroup.STOCKS,
        day_trade_group=TaxAssessmentGroup.STOCKS,
        common_rate=Decimal("0.15"),
        day_trade_rate=Decimal("0.20"),
        monthly_exemption_limit=Decimal("20000"),
    ),
    "BDR": TaxClassPolicy(
        canonical_class="BDR",
        common_group=TaxAssessmentGroup.BDR,
        day_trade_group=TaxAssessmentGroup.BDR,
        common_rate=Decimal("0.15"),
        day_trade_rate=Decimal("0.20"),
        monthly_exemption_limit=None,
    ),
    "ETF": TaxClassPolicy(
        canonical_class="ETF",
        common_group=TaxAssessmentGroup.ETF,
        day_trade_group=TaxAssessmentGroup.ETF,
        common_rate=Decimal("0.15"),
        day_trade_rate=Decimal("0.20"),
        monthly_exemption_limit=None,
    ),
    "FII": TaxClassPolicy(
        canonical_class="FII",
        common_group=TaxAssessmentGroup.REAL_ESTATE_FUNDS,
        day_trade_group=TaxAssessmentGroup.REAL_ESTATE_FUNDS,
        common_rate=Decimal("0.20"),
        day_trade_rate=Decimal("0.20"),
        monthly_exemption_limit=None,
    ),
    "FIAGRO": TaxClassPolicy(
        canonical_class="FIAGRO",
        common_group=TaxAssessmentGroup.REAL_ESTATE_FUNDS,
        day_trade_group=TaxAssessmentGroup.REAL_ESTATE_FUNDS,
        common_rate=Decimal("0.20"),
        day_trade_rate=Decimal("0.20"),
        monthly_exemption_limit=None,
    ),
}

_ALIASES = {
    "AÇÃO": "ACAO",
    "ACOES": "ACAO",
    "AÇÕES": "ACAO",
    "STOCK_BR": "ACAO",
    "FUNDO_IMOBILIARIO": "FII",
    "FUNDO IMOBILIARIO": "FII",
    "FUNDO IMOBILIÁRIO": "FII",
}


def resolve_tax_policy(asset_type: str) -> TaxClassPolicy:
    """Resolve uma política suportada sem aplicar fallback fiscal silencioso."""

    normalized = str(asset_type or "").strip().upper()
    canonical = _ALIASES.get(normalized, normalized)
    try:
        return _POLICIES[canonical]
    except KeyError as exc:
        raise ValueError(f"classe fiscal não suportada: {asset_type!r}") from exc
