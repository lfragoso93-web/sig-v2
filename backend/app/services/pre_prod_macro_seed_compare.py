"""Comparador offline de evidências do estágio macroeconômico."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.services.pre_prod_macro_seed_contract import (
    MACRO_SEED_INDICATORS,
    MACRO_SEED_SCHEMA_VERSION,
    MacroSeedContractError,
    validate_macro_seed_identity,
)


@dataclass(frozen=True)
class MacroSeedComparison:
    first_run_id: str
    second_run_id: str
    same_commit: bool
    stable_after_state: bool
    zero_new_rows_on_second_run: bool
    zero_duplicates: bool
    zero_unsupported_indicators: bool
    differences: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return (
            self.same_commit
            and self.stable_after_state
            and self.zero_new_rows_on_second_run
            and self.zero_duplicates
            and self.zero_unsupported_indicators
            and not self.differences
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "pre-prod-macro-seed-compare.v1",
            "first_run_id": self.first_run_id,
            "second_run_id": self.second_run_id,
            "same_commit": self.same_commit,
            "stable_after_state": self.stable_after_state,
            "zero_new_rows_on_second_run": self.zero_new_rows_on_second_run,
            "zero_duplicates": self.zero_duplicates,
            "zero_unsupported_indicators": self.zero_unsupported_indicators,
            "differences": list(self.differences),
            "ok": self.ok,
        }


def load_macro_seed_evidence(path: str | Path) -> dict[str, Any]:
    evidence_path = Path(path)
    try:
        payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise MacroSeedContractError(f"evidência não encontrada: {evidence_path}") from exc
    except json.JSONDecodeError as exc:
        raise MacroSeedContractError(f"evidência JSON inválida: {evidence_path}") from exc

    if not isinstance(payload, dict):
        raise MacroSeedContractError("evidência deve ser um objeto JSON")
    if payload.get("schema_version") != MACRO_SEED_SCHEMA_VERSION:
        raise MacroSeedContractError("schema_version incompatível com o estágio macro")

    validate_macro_seed_identity(
        run_id=str(payload.get("run_id", "")),
        branch=str(payload.get("branch", "")),
        commit_sha=str(payload.get("commit_sha", "")),
    )
    if payload.get("ok") is not True:
        raise MacroSeedContractError("somente evidências bem-sucedidas podem ser comparadas")
    if not isinstance(payload.get("after"), dict):
        raise MacroSeedContractError("evidência não contém estado after válido")
    if not isinstance(payload.get("imported"), dict):
        raise MacroSeedContractError("evidência não contém imported válido")
    return payload


def _canonical_state(payload: dict[str, Any]) -> dict[str, Any]:
    after = payload["after"]
    indicators = after.get("indicators")
    if not isinstance(indicators, list):
        raise MacroSeedContractError("after.indicators deve ser uma lista")

    normalized: dict[str, dict[str, Any]] = {}
    for item in indicators:
        if not isinstance(item, dict):
            raise MacroSeedContractError("cada indicador deve ser um objeto")
        name = item.get("indicator")
        if name not in MACRO_SEED_INDICATORS:
            raise MacroSeedContractError(f"indicador não suportado na evidência: {name!r}")
        normalized[name] = {
            "rows": item.get("rows"),
            "first_date": item.get("first_date"),
            "last_date": item.get("last_date"),
            "duplicate_rows": item.get("duplicate_rows"),
        }

    return {
        "total_rows": after.get("total_rows"),
        "indicators": normalized,
        "unsupported_indicators": sorted(after.get("unsupported_indicators") or []),
    }


def compare_macro_seed_evidence(
    first: dict[str, Any],
    second: dict[str, Any],
) -> MacroSeedComparison:
    differences: list[str] = []
    first_state = _canonical_state(first)
    second_state = _canonical_state(second)

    same_commit = first["commit_sha"] == second["commit_sha"]
    if not same_commit:
        differences.append("commit_sha difere entre as execuções")

    stable_after_state = first_state == second_state
    if not stable_after_state:
        differences.append("estado final difere entre as execuções")

    imported = second["imported"]
    zero_new_rows = all(int(imported.get(name, 0)) == 0 for name in MACRO_SEED_INDICATORS)
    if not zero_new_rows:
        differences.append("segunda execução importou novas linhas")

    duplicate_rows = sum(
        int(item.get("duplicate_rows", 0))
        for item in second_state["indicators"].values()
    )
    zero_duplicates = duplicate_rows == 0
    if not zero_duplicates:
        differences.append("segunda execução contém duplicidades")

    zero_unsupported = not second_state["unsupported_indicators"]
    if not zero_unsupported:
        differences.append("segunda execução contém indicadores não suportados")

    return MacroSeedComparison(
        first_run_id=first["run_id"],
        second_run_id=second["run_id"],
        same_commit=same_commit,
        stable_after_state=stable_after_state,
        zero_new_rows_on_second_run=zero_new_rows,
        zero_duplicates=zero_duplicates,
        zero_unsupported_indicators=zero_unsupported,
        differences=tuple(differences),
    )


def compare_macro_seed_files(
    first_path: str | Path,
    second_path: str | Path,
) -> MacroSeedComparison:
    return compare_macro_seed_evidence(
        load_macro_seed_evidence(first_path),
        load_macro_seed_evidence(second_path),
    )
