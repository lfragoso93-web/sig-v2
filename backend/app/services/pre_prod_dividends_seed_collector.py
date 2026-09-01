"""Coletor estrito e sem persistência para o seed isolado de proventos.

O módulo separa a orquestração de coleta das integrações e da persistência.
Provedores são injetados explicitamente, executados em sequência e devem
distinguir cobertura válida sem eventos de ausência real de cobertura.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import Any

from app.services.dividend_event_normalizer import (
    ParsedDividendEvent,
    parse_dividend_event,
)

STRICT_DIVIDENDS_ELIGIBLE_TYPES = frozenset(
    {"ACAO", "FII", "ETF_NACIONAL", "BDR"}
)

StrictDividendProvider = Callable[
    [str, str],
    Awaitable["StrictDividendProviderResult"],
]


class StrictDividendCollectionError(RuntimeError):
    """Falha bloqueante de fonte ou normalização no coletor estrito."""


@dataclass(frozen=True)
class StrictDividendAsset:
    ticker: str
    asset_type: str

    def __post_init__(self) -> None:
        normalized_ticker = self.ticker.strip().upper()
        normalized_type = self.asset_type.strip().upper()
        if not normalized_ticker:
            raise ValueError("ticker não pode ser vazio")
        if normalized_type not in STRICT_DIVIDENDS_ELIGIBLE_TYPES:
            raise ValueError(
                f"tipo de ativo inelegível para proventos: {normalized_type!r}"
            )
        object.__setattr__(self, "ticker", normalized_ticker)
        object.__setattr__(self, "asset_type", normalized_type)


@dataclass(frozen=True)
class StrictDividendProviderResult:
    source: str
    rows: tuple[dict[str, Any], ...]
    empty_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("source não pode ser vazio")
        if self.rows and self.empty_reason is not None:
            raise ValueError(
                "empty_reason só pode ser informado quando rows estiver vazio"
            )
        if not self.rows and not self.empty_reason:
            raise ValueError(
                "resposta vazia deve declarar empty_reason explicitamente"
            )


@dataclass(frozen=True)
class StrictDividendSourceCollection:
    source: str
    raw_rows: int
    normalized_rows: tuple[ParsedDividendEvent, ...]
    rejected_rows: int
    empty_reason: str | None


@dataclass(frozen=True)
class StrictDividendAssetCollection:
    ticker: str
    asset_type: str
    sources: tuple[StrictDividendSourceCollection, ...]

    @property
    def normalized_rows(self) -> int:
        return sum(len(source.normalized_rows) for source in self.sources)


def _has_authoritative_brapi_coverage(
    source: str,
    normalized_rows: tuple[ParsedDividendEvent, ...],
    empty_reason: str | None,
) -> bool:
    if source != "brapi":
        return False
    if normalized_rows:
        return True
    return not str(empty_reason or "").startswith("provider_no_coverage")


async def collect_dividends_strict(
    *,
    assets: Iterable[StrictDividendAsset],
    providers: tuple[StrictDividendProvider, ...],
) -> tuple[StrictDividendAssetCollection, ...]:
    """Coleta ativos e fontes em ordem, sem sessão ou concorrência.

    Qualquer falha de provedor ou linha inválida interrompe o estágio. Uma fonte
    sem eventos só é aceita quando declara ``empty_reason``. BRAPI é
    autoritativa quando possui cobertura; Yahoo/yfinance só pode atuar como
    fallback de ausência real de cobertura.
    """

    if not providers:
        raise ValueError("ao menos um provedor explícito é obrigatório")

    collections: list[StrictDividendAssetCollection] = []
    for asset in assets:
        source_collections: list[StrictDividendSourceCollection] = []
        seen_sources: set[str] = set()
        brapi_declared_no_coverage = False

        for provider in providers:
            try:
                response = await provider(asset.ticker, asset.asset_type)
            except StrictDividendCollectionError:
                raise
            except Exception as exc:
                provider_name = getattr(provider, "__name__", type(provider).__name__)
                raise StrictDividendCollectionError(
                    f"{asset.ticker}: provedor {provider_name} indisponível"
                ) from exc

            source = response.source.strip().lower()
            if source in seen_sources:
                raise StrictDividendCollectionError(
                    f"{asset.ticker}: fonte duplicada {source!r}"
                )
            if source == "yfinance_history" and not brapi_declared_no_coverage:
                raise StrictDividendCollectionError(
                    f"{asset.ticker}: Yahoo só pode atuar como fallback de ausência BRAPI"
                )
            seen_sources.add(source)

            normalized: list[ParsedDividendEvent] = []
            rejected = 0
            for raw_row in response.rows:
                parsed = parse_dividend_event(raw_row)
                if parsed is None:
                    rejected += 1
                    continue
                normalized.append(parsed)

            if rejected:
                raise StrictDividendCollectionError(
                    f"{asset.ticker}/{source}: {rejected} linha(s) inválida(s)"
                )

            source_collections.append(
                StrictDividendSourceCollection(
                    source=source,
                    raw_rows=len(response.rows),
                    normalized_rows=tuple(normalized),
                    rejected_rows=0,
                    empty_reason=response.empty_reason,
                )
            )
            if _has_authoritative_brapi_coverage(
                source,
                tuple(normalized),
                response.empty_reason,
            ):
                break
            if source == "brapi":
                brapi_declared_no_coverage = True

        collections.append(
            StrictDividendAssetCollection(
                ticker=asset.ticker,
                asset_type=asset.asset_type,
                sources=tuple(source_collections),
            )
        )

    return tuple(collections)
