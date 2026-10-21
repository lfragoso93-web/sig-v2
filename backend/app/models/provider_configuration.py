"""Modelo SQLAlchemy para configurações de provedores de mercado."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin


class ProviderConfiguration(Base, TimestampMixin):
    """Configuração dinâmica de provedor editável por SuperAdmin."""

    __tablename__ = "provider_configurations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider_id: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    api_key_encrypted: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    timeout_seconds: Mapped[int] = mapped_column(
        Integer, default=30, nullable=False
    )
    rate_limit_per_minute: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    custom_headers: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(50), default="PENDING", nullable=False
    )
    last_health_check_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<ProviderConfiguration provider_id={self.provider_id} "
            f"enabled={self.is_enabled}>"
        )
