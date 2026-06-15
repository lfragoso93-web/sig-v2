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
    AssetType.TESOURO_DIRETO,
    AssetType.RENDA_FIXA,
    AssetType.CRIPTO,
})

# ── Ativos que usam yfinance como provedor primário ───────────────────────────
INTL_TYPES: frozenset[AssetType] = frozenset({
    AssetType.STOCK,
    AssetType.ETF_INTERNACIONAL,
})

# ── Todos os tipos reconhecidos ───────────────────────────────────────────────
ALL_TYPES: frozenset[AssetType] = BR_TYPES | INTL_TYPES

# ── Tipos BR que têm histórico diário disponível via BRAPI Pro ───────────────
# TESOURO_DIRETO e RENDA_FIXA usam endpoints próprios (não /quote/{ticker})
BRAPI_HISTORY_TYPES: frozenset[AssetType] = frozenset({
    AssetType.ACAO,
    AssetType.FII,
    AssetType.ETF_NACIONAL,
    AssetType.CRIPTO,
})

# ── Tipos que usam sufixo .SA no yfinance (fallback histórico BR) ─────────────
YF_SA_SUFFIX_TYPES: frozenset[AssetType] = frozenset({
    AssetType.ACAO,
    AssetType.FII,
    AssetType.ETF_NACIONAL,
})

# ── Tipos que cotam em BRL ────────────────────────────────────────────────────
BRL_TYPES: frozenset[AssetType] = frozenset({
    AssetType.ACAO,
    AssetType.FII,
    AssetType.ETF_NACIONAL,
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
    if asset_type in BR_TYPES:
        return "brapi"
    if asset_type in INTL_TYPES:
        return "yfinance"
    return "brapi"  # fallback seguro para tipo desconhecido


def yf_ticker(ticker: str, asset_type: AssetType) -> str:
    """
    Converte ticker interno para formato yfinance.
    - Ações/FIIs/ETFs BR → adiciona sufixo .SA se não tiver
    - Cripto             → adiciona sufixo -USD (ex: BTC → BTC-USD)
    - Internacionais     → mantém como está
    """
    t = ticker.upper()
    if asset_type in YF_SA_SUFFIX_TYPES:
        return t if t.endswith(".SA") else f"{t}.SA"
    if asset_type == AssetType.CRIPTO:
        return t if t.endswith("-USD") else f"{t}-USD"
    return t
