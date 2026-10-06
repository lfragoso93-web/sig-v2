"""Explicit authorization context for portfolio-scoped data access."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AccessPrincipalKind(str, Enum):
    USER = "user"
    SYSTEM = "system"


class PortfolioAccessDenied(LookupError):
    """Raised without revealing whether a portfolio exists for another owner."""


@dataclass(frozen=True, slots=True)
class PortfolioAccessContext:
    principal_kind: AccessPrincipalKind
    portfolio_id: int
    permissions: frozenset[str]
    user_id: int | None = None
    purpose: str | None = None
    request_id: str | None = None

    def __post_init__(self) -> None:
        if self.portfolio_id <= 0:
            raise ValueError("portfolio_id must be positive")
        if not self.permissions:
            raise ValueError("access context requires explicit permissions")
        if self.principal_kind is AccessPrincipalKind.USER:
            if self.user_id is None or self.user_id <= 0:
                raise ValueError("user access context requires a positive user_id")
            if self.purpose is not None:
                raise ValueError("user access context cannot declare system purpose")
        elif self.principal_kind is AccessPrincipalKind.SYSTEM:
            if self.user_id is not None:
                raise ValueError("system access context cannot impersonate a user")
            if not self.purpose or not self.purpose.strip():
                raise ValueError("system access context requires an explicit purpose")

    @classmethod
    def for_user(
        cls,
        *,
        user_id: int,
        portfolio_id: int,
        permissions: frozenset[str],
        request_id: str | None = None,
    ) -> PortfolioAccessContext:
        return cls(
            principal_kind=AccessPrincipalKind.USER,
            user_id=user_id,
            portfolio_id=portfolio_id,
            permissions=permissions,
            request_id=request_id,
        )

    @classmethod
    def for_system(
        cls,
        *,
        portfolio_id: int,
        permissions: frozenset[str],
        purpose: str,
        request_id: str | None = None,
    ) -> PortfolioAccessContext:
        return cls(
            principal_kind=AccessPrincipalKind.SYSTEM,
            portfolio_id=portfolio_id,
            permissions=permissions,
            purpose=purpose,
            request_id=request_id,
        )

    def require(self, permission: str) -> None:
        if permission not in self.permissions:
            raise PortfolioAccessDenied("Carteira nao encontrada ou sem permissao")
