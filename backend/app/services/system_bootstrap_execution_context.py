"""Identidade auditável compartilhada pelo bootstrap global do SGI v2."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime

BOOTSTRAP_BRANCH = "stable-15jun"
BOOTSTRAP_COMMIT_SHA_ENV = "SGI_BOOTSTRAP_COMMIT_SHA"
DEFAULT_BOOTSTRAP_COMMIT_SHA = "0" * 40

_COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class SystemBootstrapContextError(ValueError):
    """Indica identidade incompatível com o bootstrap certificado."""


@dataclass(frozen=True)
class SystemBootstrapExecutionContext:
    run_id: str
    branch: str
    commit_sha: str

    def __post_init__(self) -> None:
        if self.branch != BOOTSTRAP_BRANCH:
            raise SystemBootstrapContextError(
                f"branch deve ser {BOOTSTRAP_BRANCH!r}"
            )
        if not _COMMIT_SHA_PATTERN.fullmatch(self.commit_sha):
            raise SystemBootstrapContextError(
                "commit_sha deve conter 40 caracteres hexadecimais minúsculos"
            )


def build_system_bootstrap_execution_context(
    *,
    commit_sha: str | None = None,
    now: datetime | None = None,
) -> SystemBootstrapExecutionContext:
    """Cria a identidade única usada por todas as etapas externas do bootstrap."""
    current = now or datetime.now(UTC)
    if commit_sha is not None:
        resolved_sha = commit_sha.strip().lower()
    else:
        env_sha = (
            os.getenv(BOOTSTRAP_COMMIT_SHA_ENV, "").strip().lower()
            or os.getenv("APP_COMMIT_SHA", "").strip().lower()
        )
        resolved_sha = (
            env_sha
            if _COMMIT_SHA_PATTERN.fullmatch(env_sha)
            else DEFAULT_BOOTSTRAP_COMMIT_SHA
        )

    if not resolved_sha:
        raise SystemBootstrapContextError(
            f"commit_sha ausente; informe-o explicitamente ou configure {BOOTSTRAP_COMMIT_SHA_ENV}"
        )

    return SystemBootstrapExecutionContext(
        run_id=current.strftime("%Y%m%d-%H%M%S"),
        branch=BOOTSTRAP_BRANCH,
        commit_sha=resolved_sha,
    )
