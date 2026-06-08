from pydantic import BaseModel, field_validator, model_validator
from datetime import date
from typing import Optional
from enum import Enum


class TransactionType(str, Enum):
    COMPRA = "COMPRA"
    VENDA = "VENDA"
    BONIFICACAO = "BONIFICACAO"
    DESDOBRAMENTO = "DESDOBRAMENTO"
    GRUPAMENTO = "GRUPAMENTO"


class TransactionCreate(BaseModel):
    portfolio_id: int
    ticker: str
    asset_type: str
    transaction_type: TransactionType
    quantity: float
    price: float                        # preco na moeda original (USD ou BRL)
    currency: str = "BRL"              # BRL ou USD
    fx_rate: Optional[float] = None    # cotacao USD/BRL editavel pelo usuario
    transaction_date: date
    broker: Optional[str] = None
    fees: Optional[float] = 0.0
    notes: Optional[str] = None
    # Campos exclusivos Renda Fixa
    issuer: Optional[str] = None
    bond_type: Optional[str] = None
    indexer: Optional[str] = None
    cdi_rate: Optional[float] = None
    bond_form: Optional[str] = None
    maturity_date: Optional[date] = None
    daily_liquidity: Optional[bool] = False

    @field_validator("ticker")
    @classmethod
    def ticker_upper(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("quantity", "price")
    @classmethod
    def positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Deve ser maior que zero")
        return v

    @model_validator(mode="after")
    def fx_required_for_usd(self):
        if self.currency == "USD" and not self.fx_rate:
            raise ValueError("fx_rate obrigatorio para transacoes em USD")
        return self

    @property
    def price_brl(self) -> float:
        if self.currency == "USD" and self.fx_rate:
            return self.price * self.fx_rate
        return self.price


class TransactionOut(BaseModel):
    id: int
    portfolio_id: int
    ticker: str
    asset_type: str
    transaction_type: str
    quantity: float
    price: float
    currency: str
    fx_rate: Optional[float]
    price_brl: Optional[float]
    total_value: float
    fees: float
    transaction_date: date
    broker: Optional[str]
    notes: Optional[str]
    average_price_after: Optional[float]

    class Config:
        from_attributes = True
