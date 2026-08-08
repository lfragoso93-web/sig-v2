"""Identidade auditável compartilhada pelo bootstrap global do SGI v2."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime

BOOTSTRAP_BRANCH = "stable-15jun"
BOOTSTRAP_COMMIT_SHA_ENV = "SGI_BOOTSTRAP_COMMIT_SHA"
BOOTSTRAP_HISTORY_START_ENV = "SGI_BOOTSTRAP_HISTORY_START_DATE"
DEFAULT_BOOTSTRAP_HISTORY_START_DATE = date(2000, 1, 1)

_COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class SystemBootstrapContextError(ValueError):
    """Indica identidade ou janela incompatível com o bootstrap certificado."""


@dataclass(frozen=True)
class SystemBootstrapExecutionContext:
    run_id: str
    branch: str
    commit_sha: str
    history_start_date: date
    history_end_date: date

    def __post_init__(self) -> None:
        if self.branch != BOOTSTRAP_BRANCH:
            raise SystemBootstrapContextError(
                f"branch deve ser {BOOTSTRAP_BRANCH!r}"
            )
        if not _COMMIT_SHA_PATTERN.fullmatch(self.commit_sha):
            raise SystemBootstrapContextError(
                "commit_sha deve conter 40 caracteres hexadecimais minúsculos"
            )
        if self.history_start_date > self.history_end_date:
            raise SystemBootstrapContextError(
                "history_start_date não pode ser posterior a history_end_date"
            )


def _parse_history_start(value: str | None) -> date:
    if not value:
        return DEFAULT_BOOTSTRAP_HISTORY_START_DATE
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SystemBootstrapContextError(
            f"{BOOTSTRAP_HISTORY_START_ENV} deve usar YYYY-MM-DD"
        ) from exc


def build_system_bootstrap_execution_context(
    *,
    commit_sha: str | None = None,
    now: datetime | None = None,
) -> SystemBootstrapExecutionContext:
    """Cria a identidade única usada por todas as etapas externas do bootstrap."""
    current = now or datetime.now(UTC)
    resolved_sha = (commit_sha or os.getenv(BOOTSTRAP_COMMIT_SHA_ENV, "")).strip().lower()
    if not resolved_sha:
        raise SystemBootstrapContextError(
            f"commit_sha ausente; informe-o explicitamente ou configure {BOOTSTRAP_COMMIT_SHA_ENV}"
        )

    history_start = _parse_history_start(os.getenv(BOOTSTRAP_HISTORY_START_ENV))
    return SystemBootstrapExecutionContext(
        run_id=current.strftime("%Y%m%d-%H%M%S"),
        branch=BOOTSTRAP_BRANCH,
        commit_sha=resolved_sha,
        history_start_date=history_start,
        history_end_date=current.date(),
    )
