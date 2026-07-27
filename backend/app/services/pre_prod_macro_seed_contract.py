"""Contrato puro do estágio isolado de séries macroeconômicas.

Este módulo não acessa banco, arquivos, rede ou variáveis de ambiente. Ele apenas
modela e valida o envelope auditável exigido pela Issue #216.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

MACRO_SEED_SCHEMA_VERSION = "pre-prod-macro-seed.v1"
MACRO_SEED_BRANCH = "stable-15jun"
MACRO_SEED_INDICATORS = ("CDI", "SELIC", "IPCA", "IGPM")
_RUN_ID_PATTERN = re.compile(r"^\d{8}-\d{6}$")
_COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class MacroSeedContractError(ValueError):
    """Indica resultado incompatível com o contrato operacional do estágio."""


def validate_macro_seed_identity(
    *,
    run_id: str,
    branch: str,
    commit_sha: str,
) -> None:
    """Valida a identidade antes de qualquer acesso operacional."""

    if not _RUN_ID_PATTERN.fullmatch(run_id):
        raise MacroSeedContractError(
            "run_id deve seguir o formato YYYYMMDD-HHMMSS"
        )
    if branch != MACRO_SEED_BRANCH:
        raise MacroSeedContractError(
            f"branch deve ser {MACRO_SEED_BRANCH!r}"
        )
    if not _COMMIT_SHA_PATTERN.fullmatch(commit_sha):
        raise MacroSeedContractError(
            "commit_sha deve conter 40 caracteres hexadecimais minúsculos"
        )


@dataclass(frozen=True)
class MacroIndicatorState:
    indicator: str
    rows: int
    first_date: str | None = None
    last_date: str | None = None
    duplicate_rows: int = 0

    def __post_init__(self) -> None:
        if self.indicator not in MACRO_SEED_INDICATORS:
            raise MacroSeedContractError(
                f"indicador não suportado: {self.indicator!r}"
            )
        if self.rows < 0:
            raise MacroSeedContractError("rows não pode ser negativo")
        if self.duplicate_rows < 0:
            raise MacroSeedContractError(
                "duplicate_rows não pode ser negativo"
            )
        if bool(self.first_date) != bool(self.last_date):
            raise MacroSeedContractError(
                "first_date e last_date devem ser informadas juntas"
            )
        if (
            self.first_date is not None
            and self.last_date is not None
            and self.first_date > self.last_date
        ):
            raise MacroSeedContractError(
                "first_date não pode ser posterior a last_date"
            )
        if self.rows == 0 and (self.first_date or self.last_date):
            raise MacroSeedContractError(
                "série vazia não pode informar cobertura temporal"
            )


@dataclass(frozen=True)
class MacroSeedState:
    total_rows: int
    indicators: tuple[MacroIndicatorState, ...]
    unsupported_indicators: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.total_rows < 0:
            raise MacroSeedContractError("total_rows não pode ser negativo")
        names = [item.indicator for item in self.indicators]
        if len(names) != len(set(names)):
            raise MacroSeedContractError(
                "indicators não pode conter séries repetidas"
            )
        if sum(item.rows for item in self.indicators) > self.total_rows:
            raise MacroSeedContractError(
                "soma das séries não pode exceder total_rows"
            )
        if len(self.unsupported_indicators) != len(set(self.unsupported_indicators)):
            raise MacroSeedContractError(
                "unsupported_indicators não pode conter duplicidades"
            )

    @property
    def duplicate_rows(self) -> int:
        return sum(item.duplicate_rows for item in self.indicators)


@dataclass(frozen=True)
class PreProdMacroSeedResult:
    run_id: str
    branch: str
    commit_sha: str
    started_at: str
    finished_at: str
    duration_seconds: float
    ok: bool
    before: MacroSeedState
    after: MacroSeedState
    imported: dict[str, int] = field(default_factory=dict)
    errors: tuple[str, ...] = ()
    schema_version: str = MACRO_SEED_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != MACRO_SEED_SCHEMA_VERSION:
            raise MacroSeedContractError(
                f"schema_version não suportado: {self.schema_version!r}"
            )
        validate_macro_seed_identity(
            run_id=self.run_id,
            branch=self.branch,
            commit_sha=self.commit_sha,
        )
        if self.duration_seconds < 0:
            raise MacroSeedContractError(
                "duration_seconds não pode ser negativo"
            )
        if self.started_at > self.finished_at:
            raise MacroSeedContractError(
                "started_at não pode ser posterior a finished_at"
            )
        if self.ok and self.errors:
            raise MacroSeedContractError(
                "resultado ok não pode conter errors"
            )
        invalid_imports = [
            indicator
            for indicator, value in self.imported.items()
            if indicator not in MACRO_SEED_INDICATORS or value < 0
        ]
        if invalid_imports:
            raise MacroSeedContractError(
                "imported contém indicador ou valor inválido: "
                + ", ".join(sorted(invalid_imports))
            )
        if self.ok:
            if self.after.duplicate_rows != 0:
                raise MacroSeedContractError(
                    "resultado ok exige duplicate_rows=0"
                )
            if self.after.unsupported_indicators:
                raise MacroSeedContractError(
                    "resultado ok não pode conter indicadores não suportados"
                )

    def to_dict(self) -> dict:
        return asdict(self)
