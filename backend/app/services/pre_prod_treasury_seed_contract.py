"""Contrato puro do estágio isolado de seed oficial do Tesouro Direto.

Este módulo não acessa banco, arquivos, rede ou variáveis de ambiente. Ele apenas
modela e valida o envelope auditável exigido pela Issue #208.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

TREASURY_SEED_SCHEMA_VERSION = "pre-prod-treasury-seed.v1"
TREASURY_SEED_BRANCH = "stable-15jun"
LEGACY_TREASURY_ASSET_IDS = (4742, 4747)
CANONICAL_TREASURY_ASSET_IDS = (4810, 4823)
_RUN_ID_PATTERN = re.compile(r"^\d{8}-\d{6}$")
_COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class TreasurySeedContractError(ValueError):
    """Indica resultado incompatível com o contrato operacional do estágio."""


def validate_treasury_seed_identity(
    *,
    run_id: str,
    branch: str,
    commit_sha: str,
) -> None:
    """Valida a identidade antes de qualquer acesso operacional."""

    if not _RUN_ID_PATTERN.fullmatch(run_id):
        raise TreasurySeedContractError(
            "run_id deve seguir o formato YYYYMMDD-HHMMSS"
        )
    if branch != TREASURY_SEED_BRANCH:
        raise TreasurySeedContractError(
            f"branch deve ser {TREASURY_SEED_BRANCH!r}"
        )
    if not _COMMIT_SHA_PATTERN.fullmatch(commit_sha):
        raise TreasurySeedContractError(
            "commit_sha deve conter 40 caracteres hexadecimais minúsculos"
        )


@dataclass(frozen=True)
class TreasurySeedCounts:
    assets: int
    aliases: int
    prices: int
    orphan_prices: int = 0
    duplicate_prices: int = 0
    legacy_assets: int = 0
    legacy_prices: int = 0

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if value < 0:
                raise TreasurySeedContractError(f"{name} não pode ser negativo")


@dataclass(frozen=True)
class TreasurySeedCoverage:
    first_price_date: str | None = None
    last_price_date: str | None = None
    priced_assets: int = 0

    def __post_init__(self) -> None:
        if self.priced_assets < 0:
            raise TreasurySeedContractError("priced_assets não pode ser negativo")
        if bool(self.first_price_date) != bool(self.last_price_date):
            raise TreasurySeedContractError(
                "first_price_date e last_price_date devem ser informadas juntas"
            )
        if (
            self.first_price_date is not None
            and self.last_price_date is not None
            and self.first_price_date > self.last_price_date
        ):
            raise TreasurySeedContractError(
                "first_price_date não pode ser posterior a last_price_date"
            )


@dataclass(frozen=True)
class PreProdTreasurySeedResult:
    run_id: str
    branch: str
    commit_sha: str
    started_at: str
    finished_at: str
    duration_seconds: float
    ok: bool
    before: TreasurySeedCounts
    after: TreasurySeedCounts
    coverage: TreasurySeedCoverage
    catalog: dict = field(default_factory=dict)
    history: dict = field(default_factory=dict)
    errors: tuple[str, ...] = ()
    schema_version: str = TREASURY_SEED_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != TREASURY_SEED_SCHEMA_VERSION:
            raise TreasurySeedContractError(
                f"schema_version não suportado: {self.schema_version!r}"
            )
        validate_treasury_seed_identity(
            run_id=self.run_id,
            branch=self.branch,
            commit_sha=self.commit_sha,
        )
        if self.duration_seconds < 0:
            raise TreasurySeedContractError("duration_seconds não pode ser negativo")
        if self.started_at > self.finished_at:
            raise TreasurySeedContractError(
                "started_at não pode ser posterior a finished_at"
            )
        if self.ok and self.errors:
            raise TreasurySeedContractError("resultado ok não pode conter errors")
        if self.ok:
            integrity = {
                "orphan_prices": self.after.orphan_prices,
                "duplicate_prices": self.after.duplicate_prices,
                "legacy_assets": self.after.legacy_assets,
                "legacy_prices": self.after.legacy_prices,
            }
            failed = [name for name, value in integrity.items() if value != 0]
            if failed:
                raise TreasurySeedContractError(
                    "resultado ok exige integridade zerada: " + ", ".join(failed)
                )
            if self.coverage.priced_assets > self.after.assets:
                raise TreasurySeedContractError(
                    "priced_assets não pode exceder a quantidade de ativos"
                )

    def to_dict(self) -> dict:
        return asdict(self)
