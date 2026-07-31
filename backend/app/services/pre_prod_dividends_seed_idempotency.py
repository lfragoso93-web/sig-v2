"""Comparação pura de evidências consecutivas do seed de proventos."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.services.pre_prod_dividends_seed_contract import (
    DIVIDENDS_SEED_SCHEMA_VERSION,
    DividendsSeedContractError,
    DividendsSeedCounts,
    DividendsSeedCoverage,
    DividendsSeedIntegrity,
    DividendsSeedTableBoundary,
    DividendsSeedTransaction,
    DividendsSeedWindow,
    PreProdDividendsSeedResult,
)

DIVIDENDS_SEED_IDEMPOTENCY_SCHEMA_VERSION = "pre-prod-dividends-seed-idempotency.v1"


@dataclass(frozen=True)
class DividendsSeedIdempotencyResult:
    first_run_id: str
    second_run_id: str
    branch: str
    commit_sha: str
    ok: bool
    same_contract: bool
    chained_baseline: bool
    stable_after_state: bool
    stable_coverage: bool
    stable_groupings: bool
    stable_sources: bool
    zero_physical_writes_on_second_run: bool
    zero_integrity_findings: bool
    errors: tuple[str, ...] = ()
    schema_version: str = DIVIDENDS_SEED_IDEMPOTENCY_SCHEMA_VERSION

    def to_dict(self) -> dict:
        return asdict(self)


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DividendsSeedContractError(f"{name} deve ser um objeto")
    return value


def _tuple_of_mappings(value: Any, name: str) -> tuple[dict, ...]:
    if not isinstance(value, (list, tuple)):
        raise DividendsSeedContractError(f"{name} deve ser uma lista")
    if not all(isinstance(item, dict) for item in value):
        raise DividendsSeedContractError(f"{name} deve conter somente objetos")
    return tuple(dict(item) for item in value)


def load_dividends_seed_evidence(
    path: str | Path,
) -> PreProdDividendsSeedResult:
    """Carrega um artefato sem acessar banco, rede ou configuração operacional."""

    evidence_path = Path(path)
    try:
        payload = json.loads(evidence_path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise DividendsSeedContractError(
            f"evidência não encontrada: {evidence_path}"
        ) from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DividendsSeedContractError(
            f"evidência JSON inválida: {evidence_path}"
        ) from exc
    if not isinstance(payload, dict):
        raise DividendsSeedContractError("evidência deve ser um objeto JSON")
    if payload.get("schema_version") != DIVIDENDS_SEED_SCHEMA_VERSION:
        raise DividendsSeedContractError(
            "schema_version incompatível com o estágio de proventos"
        )

    identity = _mapping(payload.get("identity"), "identity")
    boundary = _mapping(payload["authorized_tables"], "authorized_tables")
    return PreProdDividendsSeedResult(
        run_id=str(payload["run_id"]),
        branch=str(identity["branch"]),
        commit_sha=str(identity["commit_sha"]),
        generated_at=str(payload["generated_at"]),
        ok=payload["ok"],
        window=DividendsSeedWindow(**_mapping(payload["window"], "window")),
        before=DividendsSeedCounts(**_mapping(payload["before"], "before")),
        after=DividendsSeedCounts(**_mapping(payload["after"], "after")),
        coverage=DividendsSeedCoverage(**_mapping(payload["coverage"], "coverage")),
        integrity=DividendsSeedIntegrity(**_mapping(payload["integrity"], "integrity")),
        transaction=DividendsSeedTransaction(
            **_mapping(payload["transaction"], "transaction")
        ),
        groupings=_tuple_of_mappings(payload["groupings"], "groupings"),
        sources=_tuple_of_mappings(payload["sources"], "sources"),
        collection=dict(_mapping(payload["collection"], "collection")),
        global_persistence=dict(
            _mapping(payload["global_persistence"], "global_persistence")
        ),
        errors=tuple(str(item) for item in payload.get("errors") or ()),
        authorized_tables=DividendsSeedTableBoundary(
            read=tuple(boundary["read"]),
            write=tuple(boundary["write"]),
            inspect_only=tuple(boundary["inspect_only"]),
        ),
        schema_version=str(payload["schema_version"]),
    )


def _zero_writes(result: PreProdDividendsSeedResult) -> bool:
    try:
        return all(
            int(result.global_persistence.get(field, -1)) == 0
            for field in ("created", "updated")
        )
    except (TypeError, ValueError):
        return False


def compare_dividends_seed_runs(
    first: PreProdDividendsSeedResult,
    second: PreProdDividendsSeedResult,
) -> DividendsSeedIdempotencyResult:
    """Comprova a estabilidade de duas execuções controladas consecutivas."""

    errors: list[str] = []
    if not first.ok:
        errors.append("primeira execução não foi concluída com sucesso")
    if not second.ok:
        errors.append("segunda execução não foi concluída com sucesso")
    if first.run_id == second.run_id:
        errors.append("as execuções devem possuir run_id distintos")

    same_contract = (
        first.schema_version == second.schema_version
        and first.branch == second.branch
        and first.commit_sha == second.commit_sha
        and first.window == second.window
        and first.authorized_tables == second.authorized_tables
    )
    chained_baseline = second.before == first.after
    stable_after_state = second.after == first.after
    stable_coverage = second.coverage == first.coverage
    stable_groupings = second.groupings == first.groupings
    stable_sources = (
        second.sources == first.sources and second.collection == first.collection
    )
    zero_writes = _zero_writes(second)
    zero_integrity = (
        first.integrity.blocking_findings == 0
        and second.integrity.blocking_findings == 0
    )

    checks = (
        (same_contract, "identidade do contrato diverge entre as execuções"),
        (
            chained_baseline,
            "baseline da segunda execução diverge do estado final da primeira",
        ),
        (stable_after_state, "estado final divergiu entre as execuções"),
        (stable_coverage, "cobertura divergiu entre as execuções"),
        (stable_groupings, "agrupamentos divergiram entre as execuções"),
        (stable_sources, "fontes ou coleta divergiram entre as execuções"),
        (
            zero_writes,
            "segunda execução criou ou atualizou linhas físicas",
        ),
        (zero_integrity, "uma das execuções contém achados de integridade"),
    )
    errors.extend(message for passed, message in checks if not passed)

    return DividendsSeedIdempotencyResult(
        first_run_id=first.run_id,
        second_run_id=second.run_id,
        branch=second.branch,
        commit_sha=second.commit_sha,
        ok=not errors,
        same_contract=same_contract,
        chained_baseline=chained_baseline,
        stable_after_state=stable_after_state,
        stable_coverage=stable_coverage,
        stable_groupings=stable_groupings,
        stable_sources=stable_sources,
        zero_physical_writes_on_second_run=zero_writes,
        zero_integrity_findings=zero_integrity,
        errors=tuple(errors),
    )


def compare_dividends_seed_files(
    first_path: str | Path,
    second_path: str | Path,
) -> DividendsSeedIdempotencyResult:
    return compare_dividends_seed_runs(
        load_dividends_seed_evidence(first_path),
        load_dividends_seed_evidence(second_path),
    )
