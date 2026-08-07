from enum import Enum
from sqlalchemy import Integer, String, Text, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
from app.models.user import User


class AuditAction(str, Enum):
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    BACKUP = "BACKUP"
    RESTORE = "RESTORE"


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("idx_audit_user_date", "user_id", "created_at"),
        Index("idx_audit_resource_date", "resource_type", "created_at"),
        Index("idx_audit_action_date", "action", "created_at"),
        Index("idx_audit_portfolio_date", "portfolio_id", "created_at"),
        Index("idx_audit_status", "status"),
        Index("idx_audit_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    portfolio_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("portfolios.id", ondelete="SET NULL"), nullable=True)

    old_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    changes: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="SUCCESS")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User")
