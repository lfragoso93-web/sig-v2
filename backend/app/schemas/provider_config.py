"""Schemas Pydantic para gestão administrativa de provedores de mercado."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProviderConfigResponse(BaseModel):
    provider_id: str
    display_name: str
    description: str
    capabilities: list[str]
    is_enabled: bool
    priority: int
    base_url: str | None = None
    effective_base_url: str | None = None
    timeout_seconds: int
    rate_limit_per_minute: int | None = None
    custom_headers: dict[str, Any] | None = None
    status: str
    last_health_check_at: datetime | None = None
    last_error_message: str | None = None
    requires_auth: bool
    has_api_key_configured: bool
    api_key_masked: str | None = None
    is_official_authority: bool
    is_customized: bool
    doc_url: str | None = None


class ProviderConfigUpdate(BaseModel):
    is_enabled: bool | None = None
    priority: int | None = Field(default=None, ge=1, le=100)
    base_url: str | None = None
    timeout_seconds: int | None = Field(default=None, ge=1, le=300)
    rate_limit_per_minute: int | None = Field(default=None, ge=1)
    custom_headers: dict[str, Any] | None = None
    new_api_key: str | None = None


class ProviderTestResponse(BaseModel):
    provider_id: str
    success: bool
    status: str
    latency_ms: float
    message: str
    tested_at: datetime
