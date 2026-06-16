from pydantic import BaseModel
from typing import Optional
from app.models.asset import AssetType


class AssetBase(BaseModel):
    ticker: str
    name: str
    asset_type: AssetType
    sector: Optional[str] = None
    currency: Optional[str] = None


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    sector: Optional[str] = None
    currency: Optional[str] = None
    logo_url: Optional[str] = None


class AssetRead(AssetBase):
    id: int
    logo_url: Optional[str] = None
    last_price: Optional[float] = None

    class Config:
        from_attributes = True
