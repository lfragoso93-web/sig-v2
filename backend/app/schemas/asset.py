from pydantic import BaseModel
from app.models.asset import AssetType, AssetCurrency
from typing import Optional
from datetime import datetime


class AssetCreate(BaseModel):
    ticker: str
    name: str
    asset_type: AssetType
    currency: AssetCurrency = AssetCurrency.BRL
    brapi_ticker: Optional[str] = None
    sector: Optional[str] = None
    logo_url: Optional[str] = None


class AssetResponse(BaseModel):
    id: int
    ticker: str
    name: str
    asset_type: AssetType
    currency: AssetCurrency
    brapi_ticker: Optional[str] = None
    sector: Optional[str] = None
    logo_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
