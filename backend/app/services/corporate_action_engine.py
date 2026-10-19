"""Motor canônico e independente de provedor para eventos corporativos."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, localcontext
from enum import StrEnum
from typing import Any

from app.integrations.b3_listed_companies import parse_b3_date
from app.services.corporate_event_fractional_resolution import FractionalResolution


class CorporateActionKind(StrEnum):
    SPLIT = "DESDOBRAMENTO"
    REVERSE_SPLIT = "GRUPAMENTO"
    STOCK_BONUS = "BONIFICACAO"
    SUBSCRIPTION = "SUBSCRICAO"


class ComplexCorporateActionKind(StrEnum):
    """Classificacoes tipadas sem regra de projecao implementada."""

    INCORPORATION = "INCORPORACAO"
    SPIN_OFF = "CISAO"
    REDEMPTION = "RESGATE"


@dataclass(frozen=True)
class B3ComplexCorporateActionCandidate:
    """Fato complexo classificado, ainda sem conversao projetavel.

    `record_date` representa o ultimo dia com direito informado pela B3. A
    relacao de conversao, data efetiva e efeito em custo/caixa ficam ausentes
    ate serem demonstrados por contrato e evidencia proprios.
    """

    source: str
    source_event_id: str
    ticker: str
    source_isin: str
    record_date: date
    kind: ComplexCorporateActionKind
    destination_isins: tuple[str, ...]
    raw_payload: tuple[dict[str, Any], ...]
    quantity_factor: None = None
    effective_date: None = None

    @property
    def projectable(self) -> bool:
        return False


@dataclass(frozen=True)
class CorporateActionDestinationLeg:
    """Perna destino com conversao e rateio de custo explicitamente resolvidos."""

    destination_isin: str
    quantity_factor: Decimal
    cost_allocation: Decimal


@dataclass(frozen=True)
class ResolvedNonCashCorporateAction:
    """Contrato em memoria para uma transformacao sem componente em caixa."""

    source_event_id: str
    source_isin: str
    effective_date: date
    kind: ComplexCorporateActionKind
    destination_legs: tuple[CorporateActionDestinationLeg, ...]
    source_quantity_factor: Decimal
    source_cost_allocation: Decimal


@dataclass(frozen=True)
class NonCashCorporateActionProjection:
    """Posicoes e custos resultantes, sem persistencia ou precificacao de mercado."""

    source_isin: str
    source_quantity: Decimal
    source_cost: Decimal
    destinations: tuple[tuple[str, Decimal, Decimal], ...]
    effective_date: date
    source_event_id: str


class CorporateActionNormalizationError(ValueError):
    """Payload corporativo não satisfaz o contrato canônico."""


@dataclass(frozen=True)
class NormalizedCorporateAction:
    source: str
    source_event_id: str
    ticker: str
    event_date: date
    kind: CorporateActionKind
    quantity_factor: Decimal
    raw_payload: dict[str, Any]
    fractional_resolution: FractionalResolution | None = None

    @property
    def automatically_affects_quantity(self) -> bool:
        return self.kind != CorporateActionKind.SUBSCRIPTION


def source_payload_hash(action: NormalizedCorporateAction) -> str:
    payload = json.dumps(
        action.raw_payload,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CorporateActionProjection:
    quantity: Decimal
    total_cost: Decimal
    applied_event_ids: tuple[str, ...]
    subscription_event_ids: tuple[str, ...]

    @property
    def average_price(self) -> Decimal:
        if self.quantity <= 0:
            return Decimal(0)
        return self.total_cost / self.quantity


def _parse_date(value: object, *, field: str) -> date:
    text = str(value or "").strip()
    if not text:
        raise CorporateActionNormalizationError(f"{field} ausente")
    try:
        return date.fromisoformat(text[:10])
    except ValueError as exc:
        raise CorporateActionNormalizationError(f"{field} inválido: {text}") from exc


def _positive_decimal(value: object, *, field: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except Exception as exc:
        raise CorporateActionNormalizationError(f"{field} inválido") from exc
    if not parsed.is_finite() or parsed <= 0:
        raise CorporateActionNormalizationError(f"{field} deve ser positivo")
    return parsed


def _decimal_value(value: object, *, field: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except Exception as exc:
        raise CorporateActionNormalizationError(f"{field} invalido") from exc
    if not parsed.is_finite():
        raise CorporateActionNormalizationError(f"{field} deve ser finito")
    return parsed


def _non_negative_decimal(value: object, *, field: str) -> Decimal:
    parsed = _decimal_value(value, field=field)
    if parsed < 0:
        raise CorporateActionNormalizationError(
            f"{field} deve ser nao negativo"
        )
    return parsed


def _cost_allocation(value: object, *, field: str) -> Decimal:
    parsed = _non_negative_decimal(value, field=field)
    if parsed > 1:
        raise CorporateActionNormalizationError(
            f"{field} deve estar entre zero e um"
        )
    return parsed


def project_non_cash_corporate_action(
    *,
    quantity: Decimal,
    total_cost: Decimal,
    action: ResolvedNonCashCorporateAction,
) -> NonCashCorporateActionProjection:
    """Projeta pernas explicitamente resolvidas sem tocar no ledger ou banco.

    Conversoes de quantidade e alocacoes de custo devem vir de evidencia
    reconciliada pelo chamador. O projetor nao interpreta payload de provedor.
    """

    if action.kind not in {
        ComplexCorporateActionKind.INCORPORATION,
        ComplexCorporateActionKind.SPIN_OFF,
    }:
        raise CorporateActionNormalizationError(
            "somente incorporacao e cisao sem caixa sao suportadas"
        )
    if not action.source_event_id.strip():
        raise CorporateActionNormalizationError("source_event_id ausente")
    source_isin = action.source_isin.strip().upper()
    if len(source_isin) != 12 or not source_isin.isalnum():
        raise CorporateActionNormalizationError("source_isin invalido")
    if not isinstance(action.effective_date, date):
        raise CorporateActionNormalizationError("effective_date invalida")
    if not action.destination_legs:
        raise CorporateActionNormalizationError("perna destino ausente")

    source_quantity = _non_negative_decimal(quantity, field="quantity")
    source_cost = _non_negative_decimal(total_cost, field="total_cost")
    source_factor = _non_negative_decimal(
        action.source_quantity_factor, field="source_quantity_factor"
    )
    source_allocation = _cost_allocation(
        action.source_cost_allocation, field="source_cost_allocation"
    )
    if (
        action.kind == ComplexCorporateActionKind.INCORPORATION
        and (source_factor != 0 or source_allocation != 0)
    ):
        raise CorporateActionNormalizationError(
            "incorporacao deve extinguir quantidade e custo da origem"
        )

    normalized_legs: list[tuple[str, Decimal, Decimal]] = []
    seen_isins = {source_isin}
    allocation_total = source_allocation
    for index, leg in enumerate(action.destination_legs):
        destination_isin = leg.destination_isin.strip().upper()
        if len(destination_isin) != 12 or not destination_isin.isalnum():
            raise CorporateActionNormalizationError(
                f"destination_legs[{index}].destination_isin invalido"
            )
        if destination_isin in seen_isins:
            raise CorporateActionNormalizationError(
                "ISIN de destino duplicado ou igual a origem"
            )
        seen_isins.add(destination_isin)
        factor = _positive_decimal(
            leg.quantity_factor,
            field=f"destination_legs[{index}].quantity_factor",
        )
        allocation = _cost_allocation(
            leg.cost_allocation,
            field=f"destination_legs[{index}].cost_allocation",
        )
        normalized_legs.append((destination_isin, factor, allocation))
        allocation_total += allocation

    if allocation_total != 1:
        raise CorporateActionNormalizationError(
            "alocacoes de custo da origem e destinos devem somar um"
        )

    with localcontext() as context:
        context.prec = max(context.prec, 60)
        projected_source_quantity = source_quantity * source_factor
        projected_source_cost = source_cost * source_allocation
        destinations = tuple(
            (
                destination_isin,
                source_quantity * factor,
                source_cost * allocation,
            )
            for destination_isin, factor, allocation in normalized_legs
        )
        projected_cost = projected_source_cost + sum(
            (cost for _, _, cost in destinations), Decimal(0)
        )
        if projected_cost != source_cost:
            raise CorporateActionNormalizationError(
                "projecao nao preservou o custo total"
            )

    return NonCashCorporateActionProjection(
        source_isin=source_isin,
        source_quantity=projected_source_quantity,
        source_cost=projected_source_cost,
        destinations=destinations,
        effective_date=action.effective_date,
        source_event_id=action.source_event_id,
    )


def _event_id(
    *,
    source: str,
    ticker: str,
    kind: CorporateActionKind,
    event_date: date,
    quantity_factor: Decimal,
    payload: dict[str, Any],
) -> str:
    identity = {
        "source": source,
        "ticker": ticker,
        "kind": kind.value,
        "event_date": event_date.isoformat(),
        "quantity_factor": str(quantity_factor),
        "asset_issued": payload.get("assetIssued"),
        "isin_code": payload.get("isinCode"),
        "complete_factor": payload.get("completeFactor"),
        "provider_rate": payload.get("rate"),
    }
    digest = hashlib.sha256(
        json.dumps(identity, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    return f"{source}:{digest}"


_B3_COMPLEX_ACTION_LABELS = {
    "INCORPORACAO": ComplexCorporateActionKind.INCORPORATION,
    "CIS RED CAP": ComplexCorporateActionKind.SPIN_OFF,
    "CISAO": ComplexCorporateActionKind.SPIN_OFF,
    "CISSAO": ComplexCorporateActionKind.SPIN_OFF,
    "RESG TOTAL RV": ComplexCorporateActionKind.REDEMPTION,
    "RESGATE TOTAL": ComplexCorporateActionKind.REDEMPTION,
}
_B3_SIMPLE_ACTION_LABELS = {
    "BONIFICACAO",
    "DESDOBRAMENTO",
    "GRUPAMENTO",
    "SPLIT",
    "SUBSCRICAO",
}


def normalize_b3_complex_corporate_action_candidates(
    ticker: str,
    payload: dict[str, Any],
    *,
    expected_isin: str,
) -> tuple[B3ComplexCorporateActionCandidate, ...]:
    """Classifica fatos B3 complexos sem inventar fator ou data efetiva.

    Linhas de outras classes sao filtradas por ISIN. Linhas complexas da classe
    solicitada precisam ter data de direito; incorporacao/cisao tambem precisam
    identificar ao menos um ISIN emitido. O fator original permanece somente no
    payload bruto e nunca e disponibilizado como quantity_factor.
    """

    normalized_ticker = ticker.strip().upper()
    source_isin = expected_isin.strip().upper()
    if not normalized_ticker or not source_isin:
        raise CorporateActionNormalizationError(
            "ticker e expected_isin sao obrigatorios para a classificacao B3"
        )
    if len(source_isin) != 12 or not source_isin.isalnum():
        raise CorporateActionNormalizationError(
            "expected_isin B3 deve ter formato ISIN de 12 caracteres"
        )
    rows = payload.get("stockDividends")
    if not isinstance(rows, list):
        raise CorporateActionNormalizationError(
            "B3 stockDividends deve ser lista"
        )

    grouped: dict[
        tuple[ComplexCorporateActionKind, date, str, str],
        list[dict[str, Any]],
    ] = {}
    for raw in rows:
        if not isinstance(raw, dict):
            raise CorporateActionNormalizationError(
                "B3 stockDividends contem item invalido"
            )
        row_isin = str(raw.get("isinCode") or "").strip().upper()
        if not row_isin:
            raise CorporateActionNormalizationError(
                "B3 stockDividends sem ISIN da classe de origem"
            )
        if len(row_isin) != 12 or not row_isin.isalnum():
            raise CorporateActionNormalizationError(
                "B3 stockDividends.isinCode invalido"
            )
        if row_isin != source_isin:
            continue
        label = str(raw.get("label") or "").strip().upper()
        kind = _B3_COMPLEX_ACTION_LABELS.get(label)
        if kind is None:
            if label not in _B3_SIMPLE_ACTION_LABELS:
                raise CorporateActionNormalizationError(
                    "B3 stockDividends.label nao suportado: "
                    f"{label or 'ausente'}"
                )
            continue

        try:
            record_date = parse_b3_date(raw.get("lastDatePrior"))
        except Exception as exc:
            raise CorporateActionNormalizationError(
                "B3 acao complexa sem data de direito valida"
            ) from exc

        destination_isin = str(raw.get("assetIssued") or "").strip().upper()
        if destination_isin and (
            len(destination_isin) != 12 or not destination_isin.isalnum()
        ):
            raise CorporateActionNormalizationError(
                "B3 stockDividends.assetIssued invalido"
            )
        if kind in {
            ComplexCorporateActionKind.INCORPORATION,
            ComplexCorporateActionKind.SPIN_OFF,
        } and not destination_isin:
            raise CorporateActionNormalizationError(
                "B3 incorporacao/cisao sem ISIN do ativo emitido"
            )

        # Group rows that describe one approved event but emit multiple assets.
        group_key = (
            kind,
            record_date,
            str(raw.get("approvedOn") or "").strip(),
            str(raw.get("factor") or "").strip(),
        )
        grouped.setdefault(group_key, []).append(
            {**raw, "sourcePage": "B3 Listed Companies"}
        )

    candidates: list[B3ComplexCorporateActionCandidate] = []
    for (
        kind,
        record_date,
        _approved_on,
        _raw_factor,
    ), event_rows in grouped.items():
        ordered_rows = tuple(
            sorted(
                event_rows,
                key=lambda row: str(row.get("assetIssued") or "").upper(),
            )
        )
        destination_isins = tuple(
            sorted(
                {
                    str(row.get("assetIssued") or "").strip().upper()
                    for row in ordered_rows
                    if row.get("assetIssued")
                }
            )
        )
        if (
            kind
            in {
                ComplexCorporateActionKind.INCORPORATION,
                ComplexCorporateActionKind.SPIN_OFF,
            }
            and not destination_isins
        ):
            raise CorporateActionNormalizationError(
                "B3 incorporacao/cisao sem destino identificado"
            )
        identity_payload = {
            "source": "b3",
            "ticker": normalized_ticker,
            "source_isin": source_isin,
            "record_date": record_date.isoformat(),
            "kind": kind.value,
            "rows": ordered_rows,
        }
        encoded = json.dumps(
            identity_payload,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
            default=str,
        )
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        candidates.append(
            B3ComplexCorporateActionCandidate(
                source="b3",
                source_event_id=f"b3-complex:{digest}",
                ticker=normalized_ticker,
                source_isin=source_isin,
                record_date=record_date,
                kind=kind,
                destination_isins=destination_isins,
                raw_payload=ordered_rows,
            )
        )
    return tuple(
        sorted(
            candidates,
            key=lambda item: (item.record_date, item.source_event_id),
        )
    )


def _brapi_stock_dividend_kind(raw: dict[str, Any]) -> CorporateActionKind:
    label = str(raw.get("label") or "").strip().upper()
    if label == CorporateActionKind.REVERSE_SPLIT.value:
        return CorporateActionKind.REVERSE_SPLIT
    if label == CorporateActionKind.SPLIT.value:
        return CorporateActionKind.SPLIT
    return CorporateActionKind.STOCK_BONUS


def normalize_brapi_corporate_actions(
    ticker: str,
    payload: dict[str, Any],
) -> tuple[NormalizedCorporateAction, ...]:
    """Normaliza bonificações e subscrições da rota v2 de dividendos."""

    ticker = ticker.strip().upper()
    if not ticker:
        raise CorporateActionNormalizationError("ticker ausente")

    entries = payload.get("results")
    if not isinstance(entries, list):
        raise CorporateActionNormalizationError("results deve ser lista")

    actions: list[NormalizedCorporateAction] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        symbols = {
            str(value).upper()
            for value in (entry.get("symbol"), entry.get("requestedSymbol"))
            if value
        }
        if symbols and ticker not in symbols:
            continue
        data = entry.get("data")
        if not isinstance(data, dict):
            continue

        categories = (
            ("stockDividends", CorporateActionKind.STOCK_BONUS),
            ("subscriptions", CorporateActionKind.SUBSCRIPTION),
        )
        for key, kind in categories:
            rows = data.get(key) or []
            if not isinstance(rows, list):
                raise CorporateActionNormalizationError(f"{key} deve ser lista")
            for raw in rows:
                if not isinstance(raw, dict):
                    raise CorporateActionNormalizationError(f"{key} contém item inválido")
                event_date = _parse_date(
                    raw.get("lastDatePrior") or raw.get("exDate"),
                    field=f"{key}.lastDatePrior",
                )
                if kind == CorporateActionKind.STOCK_BONUS:
                    kind = _brapi_stock_dividend_kind(raw)
                    quantity_factor = _positive_decimal(
                        raw.get("factor"), field=f"{key}.factor"
                    )
                else:
                    # Subscrição cria um direito, não quantidade automática.
                    quantity_factor = Decimal(1)
                raw_payload = dict(raw)
                source_event_id = _event_id(
                    source="brapi",
                    ticker=ticker,
                    kind=kind,
                    event_date=event_date,
                    quantity_factor=quantity_factor,
                    payload=raw_payload,
                )
                actions.append(NormalizedCorporateAction(
                    source="brapi",
                    source_event_id=source_event_id,
                    ticker=ticker,
                    event_date=event_date,
                    kind=kind,
                    quantity_factor=quantity_factor,
                    raw_payload=raw_payload,
                ))

    return tuple(sorted(actions, key=lambda item: (item.event_date, item.source_event_id)))


def normalize_yahoo_splits(
    ticker: str,
    rows: Iterable[tuple[date, object]],
) -> tuple[NormalizedCorporateAction, ...]:
    """Normaliza fatores de split do Yahoo como multiplicadores de quantidade."""

    ticker = ticker.strip().upper()
    actions: list[NormalizedCorporateAction] = []
    for event_date, raw_factor in rows:
        factor = _positive_decimal(raw_factor, field="stock_split.factor")
        if factor == 1:
            continue
        kind = (
            CorporateActionKind.SPLIT
            if factor > 1
            else CorporateActionKind.REVERSE_SPLIT
        )
        raw_payload = {
            "eventDate": event_date.isoformat(),
            "factor": str(factor),
        }
        source_event_id = _event_id(
            source="yahoo",
            ticker=ticker,
            kind=kind,
            event_date=event_date,
            quantity_factor=factor,
            payload=raw_payload,
        )
        actions.append(NormalizedCorporateAction(
            source="yahoo",
            source_event_id=source_event_id,
            ticker=ticker,
            event_date=event_date,
            kind=kind,
            quantity_factor=factor,
            raw_payload=raw_payload,
        ))
    return tuple(sorted(actions, key=lambda item: (item.event_date, item.source_event_id)))


def normalize_b3_corporate_actions(
    ticker: str,
    payload: dict[str, Any],
    *,
    expected_isin: str | None = None,
) -> tuple[NormalizedCorporateAction, ...]:
    """Normalize official B3 actions for one identified security class."""
    ticker = ticker.strip().upper()
    if not ticker:
        raise CorporateActionNormalizationError("ticker ausente")

    expected_isin = expected_isin.strip().upper() if expected_isin else None
    source_rows: list[tuple[str, dict[str, Any]]] = []
    reported_isins: set[str] = set()
    for field in ("stockDividends", "subscriptions"):
        rows = payload.get(field)
        if not isinstance(rows, list):
            raise CorporateActionNormalizationError(f"B3 {field} deve ser lista")
        for raw in rows:
            if not isinstance(raw, dict):
                raise CorporateActionNormalizationError(f"B3 {field} item invalido")
            row_isin = str(raw.get("isinCode") or "").strip().upper()
            if not row_isin:
                raise CorporateActionNormalizationError(f"B3 {field}.isinCode ausente")
            reported_isins.add(row_isin)
            source_rows.append((field, raw))

    if expected_isin is None and len(reported_isins) > 1:
        raise CorporateActionNormalizationError(
            "B3 retornou varias classes; expected_isin obrigatorio"
        )
    if expected_isin and reported_isins and expected_isin not in reported_isins:
        raise CorporateActionNormalizationError(
            "B3 nao retornou acao identificada pelo ISIN esperado"
        )

    actions: list[NormalizedCorporateAction] = []
    for field, raw in source_rows:
        row_isin = str(raw.get("isinCode") or "").strip().upper()
        if expected_isin and row_isin != expected_isin:
            continue
        label = str(raw.get("label") or "").strip().upper()
        kind = (
            CorporateActionKind.SUBSCRIPTION
            if field == "subscriptions"
            else CorporateActionKind.STOCK_BONUS
        )
        if field == "stockDividends":
            if "GRUPAMENTO" in label:
                kind = CorporateActionKind.REVERSE_SPLIT
            elif "DESDOBRAMENTO" in label or "SPLIT" in label:
                kind = CorporateActionKind.SPLIT
            elif "BONIFICACAO" not in label:
                raise CorporateActionNormalizationError(
                    f"B3 stockDividends.label nao suportado: {label or 'ausente'}"
                )
        try:
            event_date = parse_b3_date(raw.get("lastDatePrior") or raw.get("exDate"))
        except Exception as exc:
            raise CorporateActionNormalizationError(
                f"B3 {field}.lastDatePrior invalido"
            ) from exc
        factor = Decimal(1)
        if kind != CorporateActionKind.SUBSCRIPTION:
            raw_factor = _positive_decimal(
                raw.get("factor"), field=f"B3 {field}.factor"
            )
            # B3 reports percentage for free share increases (bonus/split)
            # and a direct quantity multiplier for reverse splits.
            factor = (
                Decimal(1) + raw_factor / Decimal(100)
                if kind in {
                    CorporateActionKind.STOCK_BONUS,
                    CorporateActionKind.SPLIT,
                }
                else raw_factor
            )
        raw_payload = {
            **raw,
            "sourcePage": "B3 Listed Companies",
            "sourceIssuer": payload.get("code"),
            "sourceIsin": raw.get("isinCode"),
            "sourceOfficialRecordDate": str(raw.get("lastDatePrior") or ""),
            "sourceFactorConvention": (
                "subscription_right_not_auto_applied"
                if kind == CorporateActionKind.SUBSCRIPTION
                else "percentage_increase"
                if kind in {
                    CorporateActionKind.STOCK_BONUS,
                    CorporateActionKind.SPLIT,
                }
                else "quantity_multiplier"
            ),
            "effectiveDateResolution": "unresolved_until_b3_trading_calendar",
        }
        source_event_id = _event_id(
            source="b3", ticker=ticker, kind=kind,
            event_date=event_date, quantity_factor=factor, payload=raw_payload
        )
        actions.append(NormalizedCorporateAction(
            source="b3", source_event_id=source_event_id, ticker=ticker,
            event_date=event_date, kind=kind, quantity_factor=factor,
            raw_payload=raw_payload,
        ))
    return tuple(sorted(actions, key=lambda item: (item.event_date, item.source_event_id)))


def project_corporate_actions(
    *,
    quantity: Decimal,
    total_cost: Decimal,
    actions: Iterable[NormalizedCorporateAction],
    through_date: date,
) -> CorporateActionProjection:
    """Projeta quantidade sem alterar operações históricas ou estado derivado."""

    if quantity < 0 or total_cost < 0:
        raise ValueError("quantidade e custo devem ser não negativos")

    projected_quantity = quantity
    applied: list[str] = []
    subscriptions: list[str] = []
    ordered = sorted(actions, key=lambda item: (item.event_date, item.source_event_id))
    for action in ordered:
        if action.event_date > through_date:
            continue
        if action.kind == CorporateActionKind.SUBSCRIPTION:
            subscriptions.append(action.source_event_id)
            continue
        projected_quantity *= action.quantity_factor
        applied.append(action.source_event_id)

    return CorporateActionProjection(
        quantity=projected_quantity,
        total_cost=total_cost,
        applied_event_ids=tuple(applied),
        subscription_event_ids=tuple(subscriptions),
    )
