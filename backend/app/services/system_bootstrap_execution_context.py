"""Identidade auditável compartilhada pelo bootstrap global do SGI v2."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime

BOOTSTRAP_BRANCH = "stable-15jun"
BOOTSTRAP_COMMIT_SHA_ENV = "SGI_BOOTSTRAP_COMMIT_SHA"

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
    """Cria a identidade única usada por todas as etapas externas do bootstrap.

    Cobertura temporal não pertence a este contexto: cada domínio deve buscar a
    maior cobertura válida suportada por sua fonte canônica, sem um corte global
    arbitrário compartilhado entre preços, câmbio, Proventos ou eventos.
    """
    current = now or datetime.now(UTC)
    resolved_sha = (commit_sha or os.getenv(BOOTSTRAP_COMMIT_SHA_ENV, "")).strip().lower()
    if not resolved_sha:
        raise SystemBootstrapContextError(
            f"commit_sha ausente; informe-o explicitamente ou configure {BOOTSTRAP_COMMIT_SHA_ENV}"
        )

    return SystemBootstrapExecutionContext(
        run_id=current.strftime("%Y%m%d-%H%M%S"),
        branch=BOOTSTRAP_BRANCH,
        commit_sha=resolved_sha,
    )
