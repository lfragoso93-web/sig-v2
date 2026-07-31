"""Auditoria somente-leitura dos contratos BRAPI Pro usados pelo SGI."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from typing import Any

import httpx

from app.core.config import settings
from app.integrations.brapi_v2_client import BrapiV2Client, TickerCoverage

DividendPayloadFetcher = Callable[[str, date, date], Awaitable[dict[str, Any]]]
_EVENT_COLLECTIONS = ("cashDividends", "stockDividends", "subscriptions")
_SENSITIVE_FRAGMENTS = ("token", "authorization", "api_key", "apikey", "secret")
_SPLIT_TERMS = (
    "split",
    "reverse_split",
    "reversesplit",
    "desdobramento",
    "grupamento",
)


class BrapiContractAuditError(RuntimeError):
    """A auditoria nao conseguiu comprovar o contrato do provedor."""


@dataclass(frozen=True)
class CorporateEventContractEvidence:
    ticker: str
    status: str
    canonical_symbol: str
    asset_type: str | None
    sub_type: str | None
    available_data: dict[str, bool]
    endpoint_called: bool
    event_counts: dict[str, int]
    observed_field_paths: tuple[str, ...]
    split_evidence: tuple[str, ...]
    sanitized_samples: dict[str, dict[str, Any] | None]
    error: str | None = None


@dataclass(frozen=True)
class BrapiContractAuditReport:
    schema_version: int
    generated_at: str
    date_from: str
    date_to: str
    requested_tickers: tuple[str, ...]
    rename_count: int
    renames: tuple[dict[str, str], ...]
    evidence: tuple[CorporateEventContractEvidence, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


class BrapiStockDividendsFetcher:
    """Adaptador estrito do endpoint corporativo, exclusivo da auditoria."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        base_url: str | None = None,
        token: str | None = None,
    ) -> None:
        self._client = client
        self._base_url = (base_url or settings.BRAPI_BASE_URL).rstrip("/")
        self._token = token if token is not None else settings.BRAPI_TOKEN

    async def __call__(
        self, ticker: str, date_from: date, date_to: date
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}
        try:
            response = await self._client.get(
                f"{self._base_url}/v2/stocks/dividends",
                headers=headers,
                params={
                    "symbols": ticker,
                    "startDate": date_from.isoformat(),
                    "endDate": date_to.isoformat(),
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise BrapiContractAuditError(
                f"{ticker}: endpoint corporativo retornou HTTP {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            raise BrapiContractAuditError(
                f"{ticker}: falha de transporte no endpoint corporativo"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise BrapiContractAuditError(
                f"{ticker}: endpoint corporativo retornou JSON invalido"
            ) from exc
        if not isinstance(payload, dict) or not isinstance(
            payload.get("results"), list
        ):
            raise BrapiContractAuditError(
                f"{ticker}: envelope corporativo diverge do contrato"
            )
        return payload


async def audit_brapi_pro_contract(
    *,
    tickers: Sequence[str],
    date_from: date,
    date_to: date,
    client: BrapiV2Client,
    dividend_fetcher: DividendPayloadFetcher,
) -> BrapiContractAuditReport:
    """Gera evidencias sem persistir nem aplicar eventos em carteiras."""
    normalized = tuple(BrapiV2Client._normalize_symbols(tickers))
    if not normalized:
        raise ValueError("ao menos um ticker deve ser informado")
    if date_from > date_to:
        raise ValueError("date_from deve ser anterior ou igual a date_to")

    coverage_rows = await client.get_ticker_coverage(normalized)
    coverage_by_requested = {row.requested_symbol: row for row in coverage_rows}
    renames = await client.list_ticker_renames(
        symbols=normalized, start_date=date_from, end_date=date_to
    )

    evidence: list[CorporateEventContractEvidence] = []
    for ticker in normalized:
        coverage = coverage_by_requested.get(ticker)
        if coverage is None:
            evidence.append(_missing_coverage_evidence(ticker))
            continue
        evidence.append(
            await _audit_ticker(
                coverage=coverage,
                date_from=date_from,
                date_to=date_to,
                dividend_fetcher=dividend_fetcher,
            )
        )

    return BrapiContractAuditReport(
        schema_version=1,
        generated_at=datetime.now(UTC).isoformat(),
        date_from=date_from.isoformat(),
        date_to=date_to.isoformat(),
        requested_tickers=normalized,
        rename_count=len(renames),
        renames=tuple(
            {
                "old_symbol": item.old_symbol,
                "new_symbol": item.new_symbol,
                "canonical_symbol": item.canonical_symbol,
                "effective_date": item.effective_date.isoformat(),
            }
            for item in renames
        ),
        evidence=tuple(evidence),
    )


async def _audit_ticker(
    *,
    coverage: TickerCoverage,
    date_from: date,
    date_to: date,
    dividend_fetcher: DividendPayloadFetcher,
) -> CorporateEventContractEvidence:
    common = {
        "ticker": coverage.requested_symbol,
        "status": coverage.status,
        "canonical_symbol": coverage.symbol,
        "asset_type": coverage.asset_type,
        "sub_type": coverage.sub_type,
        "available_data": dict(coverage.available_data),
    }
    if not coverage.supports("stockDividends"):
        return CorporateEventContractEvidence(
            **common,
            endpoint_called=False,
            event_counts={name: 0 for name in _EVENT_COLLECTIONS},
            observed_field_paths=(),
            split_evidence=(),
            sanitized_samples={name: None for name in _EVENT_COLLECTIONS},
            error="coverage_without_stock_dividends",
        )

    try:
        payload = await dividend_fetcher(coverage.symbol, date_from, date_to)
        data_objects = _matching_data_objects(payload, coverage.symbol)
        counts = {
            name: sum(len(_event_rows(data, name)) for data in data_objects)
            for name in _EVENT_COLLECTIONS
        }
        paths = tuple(sorted(_collect_field_paths(data_objects)))
        split_evidence = tuple(sorted(_collect_split_evidence(data_objects)))
        samples = {
            name: _first_sanitized_sample(data_objects, name)
            for name in _EVENT_COLLECTIONS
        }
        return CorporateEventContractEvidence(
            **common,
            endpoint_called=True,
            event_counts=counts,
            observed_field_paths=paths,
            split_evidence=split_evidence,
            sanitized_samples=samples,
        )
    except BrapiContractAuditError as exc:
        return CorporateEventContractEvidence(
            **common,
            endpoint_called=True,
            event_counts={name: 0 for name in _EVENT_COLLECTIONS},
            observed_field_paths=(),
            split_evidence=(),
            sanitized_samples={name: None for name in _EVENT_COLLECTIONS},
            error=str(exc),
        )


def _matching_data_objects(
    payload: Mapping[str, Any], ticker: str
) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    for entry in payload.get("results", []):
        if not isinstance(entry, dict):
            continue
        symbol = str(entry.get("symbol") or entry.get("requestedSymbol") or "").upper()
        if symbol and symbol != ticker.upper():
            continue
        data = entry.get("data")
        if isinstance(data, dict):
            objects.append(data)
    return objects


def _event_rows(data: Mapping[str, Any], collection: str) -> list[dict[str, Any]]:
    raw = data.get(collection, [])
    if not isinstance(raw, list):
        raise BrapiContractAuditError(f"{collection}: colecao nao e uma lista")
    if any(not isinstance(item, dict) for item in raw):
        raise BrapiContractAuditError(f"{collection}: item nao e um objeto")
    return raw


def _collect_field_paths(data_objects: Sequence[Mapping[str, Any]]) -> set[str]:
    paths: set[str] = set()
    for data in data_objects:
        for collection in _EVENT_COLLECTIONS:
            for row in _event_rows(data, collection):
                _walk_paths(row, prefix=collection, result=paths)
    return paths


def _walk_paths(value: object, *, prefix: str, result: set[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}"
            result.add(path)
            _walk_paths(child, prefix=path, result=result)
    elif isinstance(value, list):
        for child in value[:1]:
            _walk_paths(child, prefix=f"{prefix}[]", result=result)


def _collect_split_evidence(data_objects: Sequence[Mapping[str, Any]]) -> set[str]:
    evidence: set[str] = set()
    for data in data_objects:
        for collection in _EVENT_COLLECTIONS:
            for row in _event_rows(data, collection):
                serialized = json.dumps(row, ensure_ascii=False, sort_keys=True).lower()
                matched = [term for term in _SPLIT_TERMS if term in serialized]
                if matched:
                    evidence.add(f"{collection}:{','.join(matched)}")
    return evidence


def _first_sanitized_sample(
    data_objects: Sequence[Mapping[str, Any]], collection: str
) -> dict[str, Any] | None:
    for data in data_objects:
        rows = _event_rows(data, collection)
        if rows:
            sanitized = _sanitize(rows[0])
            return sanitized if isinstance(sanitized, dict) else None
    return None


def _sanitize(value: object) -> object:
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]"
            if any(fragment in str(key).lower() for fragment in _SENSITIVE_FRAGMENTS)
            else _sanitize(child)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [_sanitize(child) for child in value[:3]]
    return value


def _missing_coverage_evidence(ticker: str) -> CorporateEventContractEvidence:
    return CorporateEventContractEvidence(
        ticker=ticker,
        status="missing",
        canonical_symbol=ticker,
        asset_type=None,
        sub_type=None,
        available_data={},
        endpoint_called=False,
        event_counts={name: 0 for name in _EVENT_COLLECTIONS},
        observed_field_paths=(),
        split_evidence=(),
        sanitized_samples={name: None for name in _EVENT_COLLECTIONS},
        error="coverage_result_missing",
    )
