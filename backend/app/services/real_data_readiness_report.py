"""Compose diagnostic bootstrap state with persisted certification authority."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.real_data_certification_reader import (
    RealDataCertificationIdentity,
    RealDataCertificationState,
    read_real_data_certification,
)
from app.services.system_readiness_service import (
    BootstrapReadiness,
    get_bootstrap_readiness,
)


@dataclass(frozen=True)
class RealDataReadinessReport:
    """Diagnostic report that cannot itself promote the running process."""

    bootstrap_complete: bool
    certification: RealDataCertificationState

    @property
    def eligible_for_activation(self) -> bool:
        return self.certification.ready_for_real_data

    @property
    def activation_required(self) -> bool:
        return False

    @property
    def ready_for_real_data(self) -> bool:
        return self.certification.ready_for_real_data

    def to_dict(self) -> dict[str, Any]:
        certification = asdict(self.certification)
        certification["status"] = self.certification.status.value
        return {
            "bootstrap_complete": self.bootstrap_complete,
            "certification": certification,
            "eligible_for_activation": self.eligible_for_activation,
            "activation_required": self.activation_required,
            "ready_for_real_data": self.ready_for_real_data,
        }


async def build_real_data_readiness_report(
    session: AsyncSession,
    expected: RealDataCertificationIdentity,
    *,
    bootstrap: BootstrapReadiness | None = None,
) -> RealDataReadinessReport:
    """Read persisted evidence and combine it with current bootstrap state."""

    certification = await read_real_data_certification(session, expected)
    current_bootstrap = bootstrap or get_bootstrap_readiness()
    return RealDataReadinessReport(
        bootstrap_complete=current_bootstrap.bootstrap_complete,
        certification=certification,
    )
