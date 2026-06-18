"""
Fonte única de verdade para classificação de tipos de ativo.

Regras de provedor:
  - BRAPI (plano PRO) → primária para todos os ativos BR e cripto
  - yfinance          → primária para ativos internacionais (STOCK, ETF_INTERNACIONAL)
                        fallback para ativos BR quando BRAPI falha

Nunca importar AssetType diretamente nos serviços de cotação —
usar os sets abaixo para evitar divergência entre arquivos.
"""

from app.models.asset import AssetType

# ── Ativos que usam BRAPI como provedor primário ──────────────────────────────
BR_TYPES: frozenset[AssetType] = frozenset({
    AssetType.ACAO,
    AssetType.FII,
    AssetType.ETF_NACIONAL,
    AssetType.BDR,           # BDR negocia na B3 — provedor BRAPI
    AssetType.TESOURO_DIRETO,
    AssetType.RENDA_FIXA,
    AssetType.CRIPTO,
})

# ── Ativos que usam yfinance como provedor primário ───────────────────────────
INTL_TYPES: frozenset[AssetType] = frozenset({
    AssetType.STOCK,
    AssetType.ETF_INTERNACIONAL,
})

# ── Ativos sem cotação de mercado disponível via API ─────────────────────────
# TESOURO_DIRETO e RENDA_FIXA usam endpoints próprios; OUTRO não tem ticker
NO_QUOTE_TYPES: frozenset[AssetType] = frozenset({
    AssetType.TESOURO_DIRETO,
    AssetType.RENDA_FIXA,
    AssetType.OUTRO,
})

# ── Todos os tipos reconhecidos ───────────────────────────────────────────────
ALL_TYPES: frozenset[AssetType] = BR_TYPES | INTL_TYPES | frozenset({AssetType.OUTRO})

# ── Tipos BR que têm histórico diário disponível via BRAPI Pro ───────────────
# TESOURO_DIRETO e RENDA_FIXA usam endpoints próprios (não /quote/{ticker})
BRAPI_HISTORY_TYPES: frozenset[AssetType] = frozenset({
    AssetType.ACAO,
    AssetType.FII,
    AssetType.ETF_NACIONAL,
    AssetType.BDR,
    AssetType.CRIPTO,
})

# ── Tipos que usam sufixo .SA no yfinance (fallback histórico BR) ─────────────
YF_SA_SUFFIX_TYPES: frozenset[AssetType] = frozenset({
    AssetType.ACAO,
    AssetType.FII,
    AssetType.ETF_NACIONAL,
    AssetType.BDR,
})

# ── Tipos que cotam em BRL ────────────────────────────────────────────────────
BRL_TYPES: frozenset[AssetType] = frozenset({
    AssetType.ACAO,
    AssetType.FII,
    AssetType.ETF_NACIONAL,
    AssetType.BDR,
    AssetType.TESOURO_DIRETO,
    AssetType.RENDA_FIXA,
    AssetType.CRIPTO,
})

# ── Tipos que cotam em USD ────────────────────────────────────────────────────
USD_TYPES: frozenset[AssetType] = frozenset({
    AssetType.STOCK,
    AssetType.ETF_INTERNACIONAL,
})


def provider_for(asset_type: AssetType) -> str:
    """Retorna o provedor primário para o tipo de ativo."""
    if asset_type in NO_QUOTE_TYPES:
        return "none"
    if asset_type in INTL_TYPES:
        return "yfinance"
    if asset_type in BR_TYPES:
        return "brapi"
    return "brapi"  # fallback seguro para tipo desconhecido


def yf_ticker(ticker: str, asset_type: AssetType) -> str:
    """
    Converte ticker interno para formato yfinance.
    - Ações/FIIs/ETFs BR/BDRs → adiciona sufixo .SA se não tiver
    - Cripto                   → adiciona sufixo -USD (ex: BTC → BTC-USD)
    - Internacionais           → mantém como está
    """
    t = ticker.upper()
    if asset_type in YF_SA_SUFFIX_TYPES:
        return t if t.endswith(".SA") else f"{t}.SA"
    if asset_type == AssetType.CRIPTO:
        return t if t.endswith("-USD") else f"{t}-USD"
    return t
