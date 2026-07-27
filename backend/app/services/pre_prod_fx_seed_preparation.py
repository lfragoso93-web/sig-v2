"""Preparação transacional do seed cambial pré-produção.

Este módulo conecta o cliente PTAX estrito à persistência existente sem assumir
controle da transação. O chamador continua responsável por commit ou rollback.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date as DateType

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.bcb_ptax_strict import (
    PTAX_PAIR,
    StrictPtaxRate,
    fetch_strict_usd_brl_period,
)
from app.services.fx_service import persist_usd_brl_rate

FetchRunner = Callable[
    [str | DateType, str | DateType],
    Awaitable[tuple[StrictPtaxRate, ...]],
]
PersistRunner = Callable[..., Awaitable[None]]


class FxSeedPreparationError(RuntimeError):
    """Falha ao preparar taxas cambiais para persistência transacional."""


@dataclass(frozen=True)
class FxSeedPreparationResult:
    pair: str
    requested_start_date: str
    requested_end_date: str
    fetched_rows: int
    persisted_rows: int
    first_date: str
    last_date: str

    def __post_init__(self) -> None:
        if self.pair != PTAX_PAIR:
            raise FxSeedPreparationError(f"par não suportado: {self.pair!r}")
        if self.requested_start_date > self.requested_end_date:
            raise FxSeedPreparationError(
                "requested_start_date não pode ser posterior a requested_end_date"
            )
        if self.fetched_rows <= 0:
            raise FxSeedPreparationError("fetched_rows deve ser positivo")
        if self.persisted_rows != self.fetched_rows:
            raise FxSeedPreparationError(
                "persisted_rows deve ser igual a fetched_rows"
            )
        if self.first_date > self.last_date:
            raise FxSeedPreparationError(
                "first_date não pode ser posterior a last_date"
            )
        if self.first_date < self.requested_start_date:
            raise FxSeedPreparationError(
                "first_date não pode anteceder requested_start_date"
            )
        if self.last_date > self.requested_end_date:
            raise FxSeedPreparationError(
                "last_date não pode ultrapassar requested_end_date"
            )

    def imported_counts(self) -> dict[str, int]:
        return {self.pair: self.persisted_rows}


async def prepare_pre_prod_fx_seed(
    db: AsyncSession,
    *,
    start_date: str | DateType,
    end_date: str | DateType,
    fetch_runner: FetchRunner = fetch_strict_usd_brl_period,
    persist_runner: PersistRunner = persist_usd_brl_rate,
) -> FxSeedPreparationResult:
    """Busca PTAX estrita e prepara UPSERTs sem commit ou rollback internos."""

    start = _parse_date(start_date, field_name="start_date")
    end = _parse_date(end_date, field_name="end_date")
    if start > end:
        raise FxSeedPreparationError(
            "start_date não pode ser posterior a end_date"
        )

    rows = await fetch_runner(start, end)
    if not rows:
        raise FxSeedPreparationError(
            "cliente PTAX estrito não retornou taxas para o período solicitado"
        )

    ordered_rows = tuple(sorted(rows, key=lambda item: item.rate_date))
    _validate_rows(ordered_rows, start=start, end=end)

    for row in ordered_rows:
        await persist_runner(
            db,
            row.rate_date.isoformat(),
            row.rate,
            commit=False,
        )

    return FxSeedPreparationResult(
        pair=PTAX_PAIR,
        requested_start_date=start.isoformat(),
        requested_end_date=end.isoformat(),
        fetched_rows=len(ordered_rows),
        persisted_rows=len(ordered_rows),
        first_date=ordered_rows[0].rate_date.isoformat(),
        last_date=ordered_rows[-1].rate_date.isoformat(),
    )


def _parse_date(value: str | DateType, *, field_name: str) -> DateType:
    if isinstance(value, DateType):
        return value
    try:
        return DateType.fromisoformat(str(value))
    except ValueError as exc:
        raise FxSeedPreparationError(
            f"{field_name} inválida: {value!r}"
        ) from exc


def _validate_rows(
    rows: tuple[StrictPtaxRate, ...],
    *,
    start: DateType,
    end: DateType,
) -> None:
    seen_dates: set[DateType] = set()
    for row in rows:
        if row.pair != PTAX_PAIR:
            raise FxSeedPreparationError(
                f"cliente retornou par não suportado: {row.pair!r}"
            )
        if row.rate_date < start or row.rate_date > end:
            raise FxSeedPreparationError(
                "cliente retornou taxa fora do período solicitado: "
                f"{row.rate_date.isoformat()}"
            )
        if row.rate_date in seen_dates:
            raise FxSeedPreparationError(
                "cliente retornou data duplicada: "
                f"{row.rate_date.isoformat()}"
            )
        seen_dates.add(row.rate_date)
