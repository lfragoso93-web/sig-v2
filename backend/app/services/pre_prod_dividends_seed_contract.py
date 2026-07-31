"""Contrato puro do estágio isolado de proventos.

Este módulo não acessa banco, arquivos, rede ou variáveis de ambiente. Ele
modela e valida o envelope auditável definido na Issue #226.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

DIVIDENDS_SEED_SCHEMA_VERSION = "pre-prod-dividends-seed.v1"
DIVIDENDS_SEED_BRANCH = "stable-15jun"
DIVIDENDS_SEED_READ_TABLES = (
    "assets",
    "transactions",
    "portfolios",
    "asset_dividends",
    "dividends",
)
DIVIDENDS_SEED_WRITE_TABLES = ("asset_dividends",)
DIVIDENDS_SEED_INSPECTION_TABLES = ("dividends_sync_jobs",)
_RUN_ID_PATTERN = re.compile(r"^\d{8}-\d{6}$")
_COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class DividendsSeedContractError(ValueError):
    """Indica envelope incompatível com o contrato operacional."""


def validate_dividends_seed_identity(
    *,
    run_id: str,
    branch: str,
    commit_sha: str,
) -> None:
    """Valida a identidade antes de qualquer acesso operacional."""

    if not _RUN_ID_PATTERN.fullmatch(run_id):
        raise DividendsSeedContractError("run_id deve seguir o formato YYYYMMDD-HHMMSS")
    if branch != DIVIDENDS_SEED_BRANCH:
        raise DividendsSeedContractError(f"branch deve ser {DIVIDENDS_SEED_BRANCH!r}")
    if not _COMMIT_SHA_PATTERN.fullmatch(commit_sha):
        raise DividendsSeedContractError(
            "commit_sha deve conter 40 caracteres hexadecimais minúsculos"
        )


@dataclass(frozen=True)
class DividendsSeedWindow:
    start_date: str
    end_date: str

    def __post_init__(self) -> None:
        if self.start_date > self.end_date:
            raise DividendsSeedContractError(
                "start_date não pode ser posterior a end_date"
            )


@dataclass(frozen=True)
class DividendsSeedTableBoundary:
    read: tuple[str, ...] = DIVIDENDS_SEED_READ_TABLES
    write: tuple[str, ...] = DIVIDENDS_SEED_WRITE_TABLES
    inspect_only: tuple[str, ...] = DIVIDENDS_SEED_INSPECTION_TABLES

    def __post_init__(self) -> None:
        if self.read != DIVIDENDS_SEED_READ_TABLES:
            raise DividendsSeedContractError("fronteira de leitura diverge do contrato")
        if self.write != DIVIDENDS_SEED_WRITE_TABLES:
            raise DividendsSeedContractError("fronteira de escrita diverge do contrato")
        if self.inspect_only != DIVIDENDS_SEED_INSPECTION_TABLES:
            raise DividendsSeedContractError(
                "fronteira de inspeção diverge do contrato"
            )


@dataclass(frozen=True)
class DividendsSeedCounts:
    assets: int
    transactions: int
    portfolios: int
    asset_dividends: int
    dividends: int
    sync_jobs: int

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if value < 0:
                raise DividendsSeedContractError(f"{name} não pode ser negativo")


@dataclass(frozen=True)
class DividendsSeedIntegrity:
    duplicate_global_events: int = 0
    duplicate_materializations: int = 0
    orphan_asset_dividends: int = 0
    orphan_dividend_events: int = 0
    orphan_dividend_portfolios: int = 0
    missing_ex_dates: int = 0
    negative_monetary_values: int = 0
    missing_materializations: int = 0
    materializations_without_entitlement: int = 0

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if value < 0:
                raise DividendsSeedContractError(f"{name} não pode ser negativo")

    @property
    def blocking_findings(self) -> int:
        return (
            self.duplicate_global_events
            + self.orphan_asset_dividends
            + self.missing_ex_dates
            + self.negative_monetary_values
        )


@dataclass(frozen=True)
class DividendsSeedCoverage:
    first_ex_date: str | None = None
    last_ex_date: str | None = None
    assets_with_events: int = 0
    portfolios_with_dividends: int = 0
    eligible_materializations: int = 0
    materialized_eligible_rights: int = 0

    def __post_init__(self) -> None:
        if any(
            value < 0
            for value in (
                self.assets_with_events,
                self.portfolios_with_dividends,
                self.eligible_materializations,
                self.materialized_eligible_rights,
            )
        ):
            raise DividendsSeedContractError(
                "contagens de cobertura não podem ser negativas"
            )
        if self.materialized_eligible_rights > self.eligible_materializations:
            raise DividendsSeedContractError(
                "direitos materializados elegíveis excedem a cobertura esperada"
            )
        if bool(self.first_ex_date) != bool(self.last_ex_date):
            raise DividendsSeedContractError(
                "first_ex_date e last_ex_date devem ser informadas juntas"
            )
        if (
            self.first_ex_date is not None
            and self.last_ex_date is not None
            and self.first_ex_date > self.last_ex_date
        ):
            raise DividendsSeedContractError(
                "first_ex_date não pode ser posterior a last_ex_date"
            )


@dataclass(frozen=True)
class DividendsSeedTransaction:
    final_state: str
    committed: bool
    rollback_performed: bool

    def __post_init__(self) -> None:
        if self.final_state not in {"committed", "rolled_back", "blocked"}:
            raise DividendsSeedContractError(
                f"final_state não suportado: {self.final_state!r}"
            )
        if self.committed != (self.final_state == "committed"):
            raise DividendsSeedContractError("committed diverge de final_state")
        if self.rollback_performed and self.committed:
            raise DividendsSeedContractError(
                "resultado confirmado não pode informar rollback"
            )


@dataclass(frozen=True)
class PreProdDividendsSeedResult:
    run_id: str
    branch: str
    commit_sha: str
    generated_at: str
    ok: bool
    window: DividendsSeedWindow
    before: DividendsSeedCounts
    after: DividendsSeedCounts
    coverage: DividendsSeedCoverage
    integrity: DividendsSeedIntegrity
    transaction: DividendsSeedTransaction
    groupings: tuple[dict, ...] = ()
    sources: tuple[dict, ...] = ()
    collection: dict = field(default_factory=dict)
    global_persistence: dict = field(default_factory=dict)
    materialization: dict = field(default_factory=dict)
    errors: tuple[str, ...] = ()
    authorized_tables: DividendsSeedTableBoundary = field(
        default_factory=DividendsSeedTableBoundary
    )
    schema_version: str = DIVIDENDS_SEED_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != DIVIDENDS_SEED_SCHEMA_VERSION:
            raise DividendsSeedContractError(
                f"schema_version não suportado: {self.schema_version!r}"
            )
        validate_dividends_seed_identity(
            run_id=self.run_id,
            branch=self.branch,
            commit_sha=self.commit_sha,
        )
        if self.ok and self.errors:
            raise DividendsSeedContractError("resultado ok não pode conter errors")
        if self.ok and self.integrity.blocking_findings:
            raise DividendsSeedContractError(
                "resultado ok exige integridade sem achados bloqueantes"
            )
        if self.ok and not self.transaction.committed:
            raise DividendsSeedContractError("resultado ok exige transação confirmada")

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["identity"] = {
            "branch": payload.pop("branch"),
            "commit_sha": payload.pop("commit_sha"),
        }
        return payload
