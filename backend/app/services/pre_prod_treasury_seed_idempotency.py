"""Comparação pura de duas evidências do seed isolado do Tesouro Direto."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from app.services.pre_prod_treasury_seed_contract import PreProdTreasurySeedResult

TREASURY_SEED_IDEMPOTENCY_SCHEMA_VERSION = "pre-prod-treasury-seed-idempotency.v1"


@dataclass(frozen=True)
class TreasurySeedIdempotencyResult:
    first_run_id: str
    second_run_id: str
    branch: str
    commit_sha: str
    ok: bool
    same_state: bool
    same_coverage: bool
    chained_baseline: bool
    errors: tuple[str, ...] = ()
    schema_version: str = TREASURY_SEED_IDEMPOTENCY_SCHEMA_VERSION

    def to_dict(self) -> dict:
        return asdict(self)


def compare_treasury_seed_runs(
    first: PreProdTreasurySeedResult,
    second: PreProdTreasurySeedResult,
) -> TreasurySeedIdempotencyResult:
    """Comprova idempotência estrutural entre execuções controladas consecutivas."""

    errors: list[str] = []
    if not first.ok:
        errors.append("primeira execução não foi concluída com sucesso")
    if not second.ok:
        errors.append("segunda execução não foi concluída com sucesso")
    if first.run_id == second.run_id:
        errors.append("as execuções devem possuir run_id distintos")
    if first.branch != second.branch:
        errors.append("as execuções devem usar a mesma branch")
    if first.commit_sha != second.commit_sha:
        errors.append("as execuções devem usar o mesmo commit_sha")

    chained_baseline = second.before == first.after
    same_state = second.after == first.after
    same_coverage = second.coverage == first.coverage

    if not chained_baseline:
        errors.append("baseline da segunda execução diverge do estado final da primeira")
    if not same_state:
        errors.append("estado final divergiu entre as execuções")
    if not same_coverage:
        errors.append("cobertura divergiu entre as execuções")

    return TreasurySeedIdempotencyResult(
        first_run_id=first.run_id,
        second_run_id=second.run_id,
        branch=second.branch,
        commit_sha=second.commit_sha,
        ok=not errors,
        same_state=same_state,
        same_coverage=same_coverage,
        chained_baseline=chained_baseline,
        errors=tuple(errors),
    )
