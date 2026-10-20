"""Adaptador read-only entre o catálogo global e o projetor de posições."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.corporate_event import CorporateEvent
from app.models.corporate_event_reconciliation_evidence import (
    CorporateEventReconciliationEvidence,
)
from app.services.corporate_action_engine import (
    CorporateActionKind,
    NormalizedCorporateAction,
)
from app.services.corporate_event_fractional_resolution import (
    FractionalResolution,
    FractionalResolutionPolicy,
)

_SUPPORTED_KINDS = {kind.value: kind for kind in CorporateActionKind}
_MATCHED_RECONCILIATION_STATUS = "MATCHED"
_IGNORED_EVENT_STATUS = "IGNORADO"
_LEGACY_SOURCE_PROVIDER = "legacy"
_AMOB3_LEDGER_BASIS_REQUIRED_TYPES = {"GRUPAMENTO", "DESDOBRAMENTO"}


def _normalized_text(value: object) -> str:
    raw = value.value if hasattr(value, "value") else value
    return str(raw or "").strip()


def _is_projection_eligible(event: CorporateEvent) -> bool:
    """Autoriza somente evidências reconciliadas ou compatibilidade histórica.

    Registros produzidos pelo catálogo novo precisam ser a representação canônica
    de um grupo reconciliado e não podem exigir revisão. Linhas históricas globais
    com provedor ``legacy`` permanecem projetáveis durante a contração incremental,
    exceto quando foram explicitamente ignoradas.
    """

    if _normalized_text(event.status).upper() == _IGNORED_EVENT_STATUS:
        return False

    source_provider = _normalized_text(event.source_provider).lower()
    if source_provider in {"", _LEGACY_SOURCE_PROVIDER}:
        return True

    return (
        event.is_canonical is True
        and _normalized_text(event.reconciliation_status).upper()
        == _MATCHED_RECONCILIATION_STATUS
        and event.requires_review is False
    )


def _component_bonus_projection_spec(
    event: CorporateEvent,
    evidence: CorporateEventReconciliationEvidence | None,
) -> dict[str, Any] | None:
    """Accept only the complete, issuer-referenced multi-asset contract."""

    if (
        _normalized_text(event.ticker).upper() != "KLBN11"
        or _normalized_text(event.event_type).upper() != "BONIFICACAO"
        or evidence is None
        or _normalized_text(evidence.decision).upper() != _MATCHED_RECONCILIATION_STATUS
        or _normalized_text(evidence.evidence_type).upper()
        not in {"OFFICIAL_ISSUER_DOCUMENT", "OFFICIAL_EXCHANGE_DOCUMENT"}
    ):
        return None
    payload = _raw_payload(event)
    settlement = payload.get("fractional_component_settlement")
    if not isinstance(settlement, dict):
        return None
    if (
        settlement.get("model") != "COMPONENT_BONUS_FRACTIONS_V1"
        or str(settlement.get("evidence_reference", "")).strip()
        != str(evidence.evidence_reference or "").strip()
    ):
        return None
    required = (
        "record_date",
        "credit_date",
        "settlement_date",
        "bonus_factor",
        "bonus_cost_per_share_brl",
        "unit_ticker",
        "unit_asset_type",
        "unit_isin_code",
        "unit_composition",
        "components",
    )
    if any(settlement.get(key) is None for key in required):
        return None
    if event.record_date is None or event.payment_date is None:
        return None
    components = settlement.get("components")
    composition = settlement.get("unit_composition")
    if not isinstance(components, list) or not isinstance(composition, dict):
        return None
    try:
        if str(settlement["record_date"]) != event.record_date.isoformat():
            return None
        if str(settlement["settlement_date"]) != event.payment_date.isoformat():
            return None
        if date.fromisoformat(str(settlement["credit_date"])) < event.record_date:
            return None
        if Decimal(str(settlement["bonus_factor"])) != Decimal("0.01"):
            return None
        if Decimal(str(settlement["bonus_cost_per_share_brl"])) != Decimal(
            "12.94564988922"
        ):
            return None
        if (
            date.fromisoformat(str(settlement["record_date"]))
            != date(2025, 12, 17)
            or date.fromisoformat(str(settlement["credit_date"]))
            != date(2025, 12, 22)
            or date.fromisoformat(str(settlement["settlement_date"]))
            != date(2026, 2, 24)
        ):
            return None
        component_names = set()
        for item in components:
            if not isinstance(item, dict):
                return None
            name = str(item.get("component", "")).strip().upper()
            if not name or name in component_names:
                return None
            component_names.add(name)
            if any(
                not str(item.get(key, "")).strip()
                for key in (
                    "ticker",
                    "asset_type",
                    "isin_code",
                    "units_per_position",
                    "settlement_price_brl",
                )
            ):
                return None
        if component_names != {str(key).strip().upper() for key in composition}:
            return None
        if {
            str(key).strip().upper(): Decimal(str(value))
            for key, value in composition.items()
        } != {"ON": Decimal(1), "PN": Decimal(4)}:
            return None
        if str(settlement["unit_ticker"]).strip().upper() != "KLBN11":
            return None
        if str(settlement["unit_asset_type"]).strip().upper() != "ACAO":
            return None
        component_by_name = {
            str(item["component"]).strip().upper(): item
            for item in components
        }
        official_component_facts = {
            "ON": ("KLBN3", Decimal("1"), Decimal("3.942352337")),
            "PN": ("KLBN4", Decimal("4"), Decimal("3.942611212")),
        }
        for name, (ticker, units, settlement_price) in official_component_facts.items():
            item = component_by_name.get(name, {})
            if (
                str(item.get("ticker", "")).strip().upper() != ticker
                or str(item.get("asset_type", "")).strip().upper() != "ACAO"
                or Decimal(str(item.get("units_per_position"))) != units
                or Decimal(str(item.get("settlement_price_brl")))
                != settlement_price
            ):
                return None
    except (ArithmeticError, TypeError, ValueError):
        return None
    return dict(settlement)


def _effective_date(event: CorporateEvent) -> date:
    """Require the canonical effective date; legacy mirrors are not evidence."""

    value = event.effective_date
    source_provider = _normalized_text(event.source_provider).lower()
    if value is None and source_provider in {"", _LEGACY_SOURCE_PROVIDER}:
        value = event.event_date
    if value is None:
        raise ValueError(f"evento corporativo {event.id!r} sem data efetiva")
    return value


def _quantity_factor(event: CorporateEvent) -> Decimal:
    """Resolve o fator canônico com fallback temporário para ``ratio``."""

    value = event.quantity_factor
    if value is None:
        value = event.ratio
    if value is None:
        raise ValueError(
            f"evento corporativo {event.id!r} sem fator de quantidade"
        )
    return Decimal(str(value))


def _source_identity(event: CorporateEvent) -> tuple[str, str]:
    """Prioriza a identidade neutra e reconhece registros históricos."""

    source = str(event.source_provider or "catalog")
    source_event_id = str(
        event.source_event_id
        or event.brapi_event_id
        or f"corporate-event:{event.id}"
    )
    return source, source_event_id


def _raw_payload(event: CorporateEvent) -> dict[str, Any]:
    """Prioriza metadados canônicos e lê o envelope legado somente como fallback."""

    if isinstance(event.raw_metadata, dict):
        return dict(event.raw_metadata)
    if not event.raw_data:
        return {}
    try:
        parsed = json.loads(event.raw_data)
    except (TypeError, ValueError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    provider_payload = parsed.get("provider_payload")
    if isinstance(provider_payload, dict):
        return dict(provider_payload)
    return parsed


def _fractional_resolution(
    event: CorporateEvent,
    evidence: CorporateEventReconciliationEvidence | None,
) -> FractionalResolution | None:
    """Converte evidencia MATCHED persistida no contrato puro de projecao."""

    source_provider = _normalized_text(event.source_provider).lower()
    if source_provider in {"", _LEGACY_SOURCE_PROVIDER}:
        return None

    if evidence is None:
        raise ValueError(
            f"evento corporativo MATCHED {event.id!r} sem evidencia de reconciliacao"
        )

    if _normalized_text(evidence.decision).upper() != _MATCHED_RECONCILIATION_STATUS:
        raise ValueError(
            f"evento corporativo MATCHED {event.id!r} com evidencia nao-MATCHED"
        )

    try:
        policy = FractionalResolutionPolicy(
            _normalized_text(evidence.fractional_policy).upper()
        )
    except ValueError as exc:
        raise ValueError(
            f"evento corporativo MATCHED {event.id!r} com politica fracionaria invalida"
        ) from exc

    if policy == FractionalResolutionPolicy.MANUAL_REVIEW:
        raise ValueError(
            f"evento corporativo MATCHED {event.id!r} nao aceita MANUAL_REVIEW"
        )

    ticker = _normalized_text(event.ticker).upper()
    event_type = _normalized_text(event.event_type).upper()
    ledger_basis = _normalized_text(
        getattr(evidence, "ledger_basis", None)
    ).upper()
    if (
        ticker == "AMOB3"
        and event_type in _AMOB3_LEDGER_BASIS_REQUIRED_TYPES
        and not ledger_basis
    ):
        raise ValueError(
            f"evento corporativo MATCHED {event.id!r} AMOB3 exige base do ledger"
        )

    return FractionalResolution(
        policy=policy,
        fractional_quantity=(
            Decimal(str(evidence.fractional_quantity))
            if evidence.fractional_quantity is not None
            else None
        ),
        settlement_price=(
            Decimal(str(evidence.fractional_settlement_price))
            if evidence.fractional_settlement_price is not None
            else None
        ),
        cash_treatment=(
            str(evidence.cash_treatment)
            if evidence.cash_treatment is not None
            else None
        ),
        ledger_basis=(ledger_basis or None),
        fraction_is_post_event_quantity=bool(
            _normalized_text(event.source_provider).lower() == "b3"
            and ledger_basis == "ADJUSTED_POST_EVENT"
        ),
    )


async def load_global_corporate_actions_by_ticker(
    db: AsyncSession,
    tickers: list[str],
) -> dict[str, tuple[NormalizedCorporateAction, ...]]:
    """Carrega eventos globais elegíveis para o motor puro.

    Linhas vinculadas a carteira, conflitos, evidências não canônicas e eventos
    pendentes de revisão ficam fora da projeção. A única exceção é a compatibilidade
    explícita para registros históricos globais marcados como ``legacy``.
    """

    normalized_tickers = sorted(
        {ticker.strip().upper() for ticker in tickers if ticker}
    )
    if not normalized_tickers:
        return {}

    result = await db.execute(
        select(
            CorporateEvent,
            CorporateEventReconciliationEvidence,
        )
        .outerjoin(
            CorporateEventReconciliationEvidence,
            CorporateEventReconciliationEvidence.corporate_event_id
            == CorporateEvent.id,
        )
        .where(
            CorporateEvent.ticker.in_(normalized_tickers),
            CorporateEvent.portfolio_id.is_(None),
        )
    )

    rows = result.all()
    configured: dict[int, dict[str, Any]] = {}
    identity_tickers: set[str] = set()
    for event, evidence in rows:
        spec = _component_bonus_projection_spec(event, evidence)
        if spec is None:
            continue
        configured[int(event.id)] = spec
        identity_tickers.add(str(spec["unit_ticker"]).strip().upper())
        for component in spec["components"]:
            identity_tickers.add(str(component["ticker"]).strip().upper())

    catalog_by_identity: dict[tuple[str, str], str | None] = {}
    if identity_tickers:
        asset_result = await db.execute(
            select(Asset).where(
                func.upper(func.trim(Asset.ticker)).in_(identity_tickers)
            )
        )
        for asset in asset_result.scalars().all():
            catalog_by_identity[
                (
                    str(asset.ticker).strip().upper(),
                    _normalized_text(asset.asset_type).upper(),
                )
            ] = str(asset.isin_code or "").strip().upper() or None

    actions: dict[str, list[NormalizedCorporateAction]] = {}
    for event, evidence in rows:
        if not _is_projection_eligible(event):
            continue

        component_bonus = configured.get(int(event.id))
        if (
            _normalized_text(event.ticker).upper() == "KLBN11"
            and _normalized_text(event.event_type).upper() == "BONIFICACAO"
            and component_bonus is None
        ):
            # Never send a KLBN11 bonus through the homogeneous ticker factor.
            continue
        if component_bonus is not None:
            expected_unit = (
                str(component_bonus["unit_ticker"]).strip().upper(),
                str(component_bonus["unit_asset_type"]).strip().upper(),
            )
            if catalog_by_identity.get(expected_unit) != str(
                component_bonus["unit_isin_code"]
            ).strip().upper():
                continue
            if (
                event.isin_code
                and str(event.isin_code).strip().upper()
                != str(component_bonus["unit_isin_code"]).strip().upper()
            ):
                continue
            if any(
                catalog_by_identity.get(
                    (
                        str(component["ticker"]).strip().upper(),
                        str(component["asset_type"]).strip().upper(),
                    )
                )
                != str(component["isin_code"]).strip().upper()
                for component in component_bonus["components"]
            ):
                continue

        kind = _SUPPORTED_KINDS.get(str(event.event_type).upper())
        if kind is None:
            continue

        source, source_event_id = _source_identity(event)
        ticker = str(event.ticker).strip().upper()
        actions.setdefault(ticker, []).append(
            NormalizedCorporateAction(
                source=source,
                source_event_id=source_event_id,
                ticker=ticker,
                event_date=_effective_date(event),
                kind=kind,
                quantity_factor=_quantity_factor(event),
                raw_payload=_raw_payload(event),
                fractional_resolution=(
                    None
                    if component_bonus is not None
                    else _fractional_resolution(event, evidence)
                ),
                component_bonus=component_bonus,
            )
        )

    return {
        ticker: tuple(
            sorted(
                rows,
                key=lambda item: (item.event_date, item.source_event_id),
            )
        )
        for ticker, rows in actions.items()
    }
