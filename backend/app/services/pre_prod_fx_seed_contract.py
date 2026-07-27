"""Contrato puro do estágio isolado de câmbio.

Este módulo não acessa banco, arquivos, rede ou variáveis de ambiente. Ele apenas
modela e valida o envelope auditável exigido pela Issue #217.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

FX_SEED_SCHEMA_VERSION = "pre-prod-fx-seed.v1"
FX_SEED_BRANCH = "stable-15jun"
FX_SEED_PAIRS = ("USD-BRL",)
FX_SEED_RATE_TYPE = "PTAX_SELL"
FX_SEED_SOURCE = "BCB"
_RUN_ID_PATTERN = re.compile(r"^\d{8}-\d{6}$")
_COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class FxSeedContractError(ValueError):
    """Indica resultado incompatível com o contrato operacional do estágio."""


def validate_fx_seed_identity(
    *,
    run_id: str,
    branch: str,
    commit_sha: str,
) -> None:
    """Valida a identidade antes de qualquer acesso operacional."""

    if not _RUN_ID_PATTERN.fullmatch(run_id):
        raise FxSeedContractError(
            "run_id deve seguir o formato YYYYMMDD-HHMMSS"
        )
    if branch != FX_SEED_BRANCH:
        raise FxSeedContractError(
            f"branch deve ser {FX_SEED_BRANCH!r}"
        )
    if not _COMMIT_SHA_PATTERN.fullmatch(commit_sha):
        raise FxSeedContractError(
            "commit_sha deve conter 40 caracteres hexadecimais minúsculos"
        )


@dataclass(frozen=True)
class FxPairState:
    pair: str
    rows: int
    first_date: str | None = None
    last_date: str | None = None
    duplicate_rows: int = 0

    def __post_init__(self) -> None:
        if self.pair not in FX_SEED_PAIRS:
            raise FxSeedContractError(
                f"par cambial não suportado: {self.pair!r}"
            )
        if self.rows < 0:
            raise FxSeedContractError("rows não pode ser negativo")
        if self.duplicate_rows < 0:
            raise FxSeedContractError(
                "duplicate_rows não pode ser negativo"
            )
        if bool(self.first_date) != bool(self.last_date):
            raise FxSeedContractError(
                "first_date e last_date devem ser informadas juntas"
            )
        if (
            self.first_date is not None
            and self.last_date is not None
            and self.first_date > self.last_date
        ):
            raise FxSeedContractError(
                "first_date não pode ser posterior a last_date"
            )
        if self.rows == 0 and (self.first_date or self.last_date):
            raise FxSeedContractError(
                "série cambial vazia não pode informar cobertura temporal"
            )


@dataclass(frozen=True)
class FxSeedState:
    total_rows: int
    pairs: tuple[FxPairState, ...]
    unsupported_pairs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.total_rows < 0:
            raise FxSeedContractError("total_rows não pode ser negativo")
        names = [item.pair for item in self.pairs]
        if len(names) != len(set(names)):
            raise FxSeedContractError(
                "pairs não pode conter pares repetidos"
            )
        if sum(item.rows for item in self.pairs) > self.total_rows:
            raise FxSeedContractError(
                "soma dos pares não pode exceder total_rows"
            )
        if len(self.unsupported_pairs) != len(set(self.unsupported_pairs)):
            raise FxSeedContractError(
                "unsupported_pairs não pode conter duplicidades"
            )

    @property
    def duplicate_rows(self) -> int:
        return sum(item.duplicate_rows for item in self.pairs)


@dataclass(frozen=True)
class PreProdFxSeedResult:
    run_id: str
    branch: str
    commit_sha: str
    started_at: str
    finished_at: str
    duration_seconds: float
    ok: bool
    before: FxSeedState
    after: FxSeedState
    imported: dict[str, int] = field(default_factory=dict)
    errors: tuple[str, ...] = ()
    source: str = FX_SEED_SOURCE
    rate_type: str = FX_SEED_RATE_TYPE
    schema_version: str = FX_SEED_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != FX_SEED_SCHEMA_VERSION:
            raise FxSeedContractError(
                f"schema_version não suportado: {self.schema_version!r}"
            )
        validate_fx_seed_identity(
            run_id=self.run_id,
            branch=self.branch,
            commit_sha=self.commit_sha,
        )
        if self.source != FX_SEED_SOURCE:
            raise FxSeedContractError(
                f"source deve ser {FX_SEED_SOURCE!r}"
            )
        if self.rate_type != FX_SEED_RATE_TYPE:
            raise FxSeedContractError(
                f"rate_type deve ser {FX_SEED_RATE_TYPE!r}"
            )
        if self.duration_seconds < 0:
            raise FxSeedContractError(
                "duration_seconds não pode ser negativo"
            )
        if self.started_at > self.finished_at:
            raise FxSeedContractError(
                "started_at não pode ser posterior a finished_at"
            )
        if self.ok and self.errors:
            raise FxSeedContractError(
                "resultado ok não pode conter errors"
            )
        invalid_imports = [
            pair
            for pair, value in self.imported.items()
            if pair not in FX_SEED_PAIRS or value < 0
        ]
        if invalid_imports:
            raise FxSeedContractError(
                "imported contém par ou valor inválido: "
                + ", ".join(sorted(invalid_imports))
            )
        if self.ok:
            if self.after.duplicate_rows != 0:
                raise FxSeedContractError(
                    "resultado ok exige duplicate_rows=0"
                )
            if self.after.unsupported_pairs:
                raise FxSeedContractError(
                    "resultado ok não pode conter pares não suportados"
                )

    def to_dict(self) -> dict:
        return asdict(self)
