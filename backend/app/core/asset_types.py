"""
Fonte única de verdade para classificação de tipos de ativo.

Regras de provedor:
  - BRAPI (plano PRO) → primária para ativos BR e cripto
  - yfinance          → primária para ativos internacionais (STOCK, ETF_INTERNACIONAL)
                         fallback para ativos BR quando BRAPI falha
  - Tesouro Direto    → serviço dedicado BRAPI Treasury, nunca o sincronizador genérico

Nunca importar AssetType diretamente nos serviços de cotação —
usar os sets abaixo para evitar divergência entre arquivos.
"""

from app.models.asset import AssetType

# Rótulos públicos canônicos. APIs e componentes de apresentação devem
# reutilizar este catálogo em vez de manter mapas locais divergentes.
ASSET_TYPE_LABELS: dict[AssetType, str] = {
    AssetType.ACAO: "Ações",
    AssetType.FII: "FIIs",
    AssetType.ETF_NACIONAL: "ETFs nacionais",
    AssetType.ETF_INTERNACIONAL: "ETFs internacionais",
    AssetType.STOCK: "Stocks",
    AssetType.CRIPTO: "Criptomoedas",
    AssetType.TESOURO_DIRETO: "Tesouro Direto",
    AssetType.RENDA_FIXA: "Renda fixa",
    AssetType.BDR: "BDRs",
    AssetType.OUTRO: "Outros",
}


def asset_type_label(asset_type: AssetType | str) -> str:
    """Retorna o rótulo canônico, preservando tipos futuros desconhecidos."""
    try:
        normalized = asset_type if isinstance(asset_type, AssetType) else AssetType(asset_type)
    except ValueError:
        return str(asset_type).replace("_", " ").title()
    return ASSET_TYPE_LABELS[normalized]

# ── Ativos que usam BRAPI como provedor primário ──────────────────────────────
# RENDA_FIXA removido daqui — não tem cotação de mercado (está em NO_QUOTE_TYPES)
BR_TYPES: frozenset[AssetType] = frozenset({
    AssetType.ACAO,
    AssetType.FII,
    AssetType.ETF_NACIONAL,
    AssetType.BDR,
    AssetType.TESOURO_DIRETO,
    AssetType.CRIPTO,
})

# ── Ativos que usam yfinance como provedor primário ───────────────────────────
INTL_TYPES: frozenset[AssetType] = frozenset({
    AssetType.STOCK,
    AssetType.ETF_INTERNACIONAL,
})

# ── Ativos sem cotação de mercado disponível via API ─────────────────────────
NO_QUOTE_TYPES: frozenset[AssetType] = frozenset({
    AssetType.RENDA_FIXA,
    AssetType.OUTRO,
})

# ── Tipos tratados por pipeline dedicado e excluídos do gap sync genérico ─────
DEDICATED_PRICE_TYPES: frozenset[AssetType] = frozenset({
    AssetType.TESOURO_DIRETO,
})

# ── Tipos que usam o endpoint de Tesouro Direto da BRAPI ──────────────────────
TREASURY_TYPES: frozenset[AssetType] = DEDICATED_PRICE_TYPES

# ── Todos os tipos reconhecidos ───────────────────────────────────────────────
ALL_TYPES: frozenset[AssetType] = BR_TYPES | INTL_TYPES | frozenset({AssetType.OUTRO})

# ── Tipos com histórico diário no sincronizador BRAPI genérico ────────────────
BRAPI_HISTORY_TYPES: frozenset[AssetType] = frozenset({
    AssetType.ACAO,
    AssetType.FII,
    AssetType.ETF_NACIONAL,
    AssetType.BDR,
    AssetType.CRIPTO,
})

# ── Tipos que usam sufixo .SA no yfinance ─────────────────────────────────────
YF_SA_SUFFIX_TYPES: frozenset[AssetType] = frozenset({
    AssetType.ACAO,
    AssetType.FII,
    AssetType.ETF_NACIONAL,
    AssetType.BDR,
})

BRL_TYPES: frozenset[AssetType] = frozenset({
    AssetType.ACAO,
    AssetType.FII,
    AssetType.ETF_NACIONAL,
    AssetType.BDR,
    AssetType.TESOURO_DIRETO,
    AssetType.RENDA_FIXA,
    AssetType.CRIPTO,
})

USD_TYPES: frozenset[AssetType] = frozenset({
    AssetType.STOCK,
    AssetType.ETF_INTERNACIONAL,
})


def provider_for(asset_type: AssetType) -> str:
    if asset_type in NO_QUOTE_TYPES:
        return "none"
    if asset_type in TREASURY_TYPES:
        return "brapi_treasury"
    if asset_type in INTL_TYPES:
        return "yfinance"
    if asset_type in BR_TYPES:
        return "brapi"
    return "brapi"


def yf_ticker(ticker: str, asset_type: AssetType) -> str:
    t = ticker.upper()
    if asset_type in YF_SA_SUFFIX_TYPES:
        return t if t.endswith(".SA") else f"{t}.SA"
    if asset_type == AssetType.CRIPTO:
        return t if t.endswith("-USD") else f"{t}-USD"
    return t
