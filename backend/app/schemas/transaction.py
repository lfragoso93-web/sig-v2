from pydantic import BaseModel, field_validator
from decimal import Decimal
from typing import Literal, Optional, List
from datetime import date as DateType
from app.schemas.fixed_income_contract import FixedIncomeContractCreate

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
    date:       DateType
    currency:   Optional[str]  = "BRL"
    notes:      Optional[str]  = None
    fixed_income_contract_id: Optional[int] = None
    fixed_income_contract: Optional[FixedIncomeContractCreate] = None

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
    date:       Optional[DateType]  = None
    currency:   Optional[str]   = None
    notes:      Optional[str]   = None
    fixed_income_contract_id: Optional[int] = None
    fixed_income_contract: Optional[FixedIncomeContractCreate] = None

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
    date:         DateType
    currency:     str
    notes:        Optional[str]
    fixed_income_contract_id: Optional[int] = None

    model_config = {"from_attributes": True}


class PagedTransactions(BaseModel):
    items:     List[TransactionOut]
    total:     int
    page:      int
    page_size: int
    pages:     int


class CorporateLifecycleEventOut(BaseModel):
    source_event_id: str
    ticker: str
    event_date: DateType
    event_type: str
    quantity_factor: Decimal
    fractional_quantity: Optional[Decimal] = None
    settlement_status: Optional[Literal["SETTLED", "PENDING_VALUE"]] = None
    unit_settlement_price_brl: Optional[Decimal] = None
    gross_amount_brl: Optional[Decimal] = None
    cost_basis_brl: Optional[Decimal] = None
    realized_pnl_brl: Optional[Decimal] = None
    cash_treatment: Optional[str] = None
    message: Optional[str] = None


class UpcomingCorporateEventOut(BaseModel):
    event_id: int
    ticker: str
    event_type: str
    event_date: DateType
    description: Optional[str] = None


class CorporateActionComponentRightOut(BaseModel):
    component: str
    bonus_quantity: Decimal
    whole_quantity: Decimal
    fractional_quantity: Decimal
    whole_units_formed: Decimal
    component_shares_in_units: Decimal
    residual_whole_quantity: Decimal
    settlement_price_brl: Decimal
    gross_amount_brl: Decimal
    attributed_cost_brl: Decimal
    fractional_cost_basis_brl: Decimal
    estimated_fractional_result_brl: Decimal


class PortfolioCorporateRightOut(BaseModel):
    event_id: int
    source_event_id: str
    ticker: str
    event_type: str
    record_date: DateType
    settlement_date: DateType
    base_position: Decimal
    settlement_status: Literal["PENDING", "AVAILABLE"]
    components: List[CorporateActionComponentRightOut]
    gross_amount_brl: Decimal
    calculated_gross_amount_brl: Decimal
    bonus_cost_per_share_brl: Decimal
    attributed_bonus_cost_brl: Decimal
    fractional_cost_basis_brl: Decimal
    estimated_fractional_result_brl: Decimal
    cash_status: Literal["CALCULATED_NOT_CONFIRMED"]
    cash_treatment: str
    evidence_reference: str
