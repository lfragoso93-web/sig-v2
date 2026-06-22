from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import date

VALID_OPERATIONS = {"buy", "sell"}
VALID_ASSET_TYPES = {
    "ACAO", "FII", "ETF_NACIONAL", "ETF_INTERNACIONAL",
    "STOCK", "BDR", "CRIPTO", "RENDA_FIXA", "TESOURO_DIRETO", "OUTRO",
}

# Mapa de normalizacao de operation (aceita variacoes comuns do frontend/importacao)
_OP_ALIASES: dict[str, str] = {
    "buy": "buy",
    "compra": "buy",
    "BUY": "buy",
    "COMPRA": "buy",
    "sell": "sell",
    "venda": "sell",
    "SELL": "sell",
    "VENDA": "sell",
}


class TransactionCreate(BaseModel):
    ticker:     str
    asset_type: str
    operation:  str
    quantity:   float
    price:      float
    fees:       Optional[float] = 0.0
    date:       date
    currency:   Optional[str]  = "BRL"
    notes:      Optional[str]  = None

    @field_validator("operation", mode="before")
    @classmethod
    def normalize_operation(cls, v: str) -> str:
        normalized = _OP_ALIASES.get(str(v))
        if normalized is None:
            raise ValueError(
                f"operation invalida: '{v}'. Valores aceitos: {sorted(VALID_OPERATIONS)}"
            )
        return normalized

    @field_validator("asset_type", mode="before")
    @classmethod
    def validate_asset_type(cls, v: str) -> str:
        val = str(v).upper()
        if val not in VALID_ASSET_TYPES:
            raise ValueError(
                f"asset_type invalido: '{v}'. Valores aceitos: {sorted(VALID_ASSET_TYPES)}"
            )
        return val


class TransactionUpdate(BaseModel):
    ticker:     Optional[str]   = None
    asset_type: Optional[str]   = None
    operation:  Optional[str]   = None
    quantity:   Optional[float] = None
    price:      Optional[float] = None
    fees:       Optional[float] = None
    date:       Optional[date]  = None
    currency:   Optional[str]   = None
    notes:      Optional[str]   = None

    @field_validator("operation", mode="before")
    @classmethod
    def normalize_operation(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        normalized = _OP_ALIASES.get(str(v))
        if normalized is None:
            raise ValueError(
                f"operation invalida: '{v}'. Valores aceitos: {sorted(VALID_OPERATIONS)}"
            )
        return normalized

    @field_validator("asset_type", mode="before")
    @classmethod
    def validate_asset_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        val = str(v).upper()
        if val not in VALID_ASSET_TYPES:
            raise ValueError(
                f"asset_type invalido: '{v}'. Valores aceitos: {sorted(VALID_ASSET_TYPES)}"
            )
        return val


class TransactionOut(BaseModel):
    id:           int
    portfolio_id: int
    ticker:       str
    asset_type:   str
    operation:    str
    quantity:     float
    price:        float
    fees:         float
    date:         date
    currency:     str
    notes:        Optional[str]

    model_config = {"from_attributes": True}


class PagedTransactions(BaseModel):
    items:     List[TransactionOut]
    total:     int
    page:      int
    page_size: int
    pages:     int
