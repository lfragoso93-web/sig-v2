"""Limpeza transacional e auditável de dois ativos legados do Tesouro Educa+.

O serviço é intencionalmente específico: qualquer divergência do conjunto aprovado
interrompe a operação antes de escrita. Dry-run é o comportamento padrão da CLI.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable

from sqlalchemy import Connection, text

SCHEMA_VERSION = "treasury-legacy-cleanup.v1"
ASSET_TYPE = "TESOURO_DIRETO"
OFFICIAL_SOURCE = "tesouro_transparente"
LEGACY_SOURCE = "brapi_treasury"


@dataclass(frozen=True)
class LegacyMapping:
    legacy_id: int
    legacy_ticker: str
    canonical_id: int
    canonical_ticker: str
    expected_close: Decimal


MAPPINGS = (
    LegacyMapping(4742, "tesouro-educa-15122030", 4810, "tesouro-educa-mais-2030", Decimal("3518.20")),
    LegacyMapping(4747, "tesouro-educa-15122031", 4823, "tesouro-educa-mais-2031", Decimal("3769.72")),
)

FUNCTIONAL_REFERENCES = (
    ("asset_dividends", "asset_id"),
    ("corporate_events", "asset_id"),
    ("portfolio_positions", "asset_id"),
    ("transactions", "asset_id"),
    ("dividends", "asset_id"),
)


class TreasuryLegacyCleanupError(RuntimeError):
    """Falha fechada de pré-condição, pós-condição ou execução."""


def _scalar(connection: Connection, sql: str, **params: Any) -> Any:
    return connection.execute(text(sql), params).scalar_one()


def _asset(connection: Connection, asset_id: int) -> dict[str, Any] | None:
    row = connection.execute(
        text("SELECT id, ticker, asset_type FROM assets WHERE id = :asset_id"),
        {"asset_id": asset_id},
    ).mappings().one_or_none()
    return dict(row) if row else None


def _table_exists(connection: Connection, table_name: str) -> bool:
    return bool(_scalar(connection, "SELECT to_regclass(:table_name) IS NOT NULL", table_name=table_name))


def _reference_counts(connection: Connection) -> dict[str, int]:
    legacy_ids = tuple(item.legacy_id for item in MAPPINGS)
    counts: dict[str, int] = {}
    for table_name, column_name in FUNCTIONAL_REFERENCES:
        if not _table_exists(connection, table_name):
            continue
        key = f"{table_name}.{column_name}"
        counts[key] = int(
            _scalar(
                connection,
                f"SELECT count(*) FROM {table_name} WHERE {column_name} IN :legacy_ids",
                legacy_ids=legacy_ids,
            )
        )
    return counts


def _price_snapshot(connection: Connection, asset_id: int, source: str) -> dict[str, Any]:
    row = connection.execute(
        text(
            """
            SELECT count(*) AS count,
                   count(*) FILTER (WHERE open IS NOT NULL OR high IS NOT NULL OR low IS NOT NULL OR volume IS NOT NULL) AS enriched,
                   min(close) AS min_close,
                   max(close) AS max_close,
                   min(timestamp) AS min_timestamp,
                   max(timestamp) AS max_timestamp
              FROM asset_prices
             WHERE asset_id = :asset_id AND source = :source
            """
        ),
        {"asset_id": asset_id, "source": source},
    ).mappings().one()
    return dict(row)


def _alias_snapshot(connection: Connection, alias_ticker: str) -> list[dict[str, Any]]:
    rows = connection.execute(
        text(
            """
            SELECT id, asset_id, alias_ticker, asset_type, source_provider
              FROM asset_aliases
             WHERE alias_ticker = :alias_ticker AND asset_type = :asset_type
             ORDER BY id
            """
        ),
        {"alias_ticker": alias_ticker, "asset_type": ASSET_TYPE},
    ).mappings()
    return [dict(row) for row in rows]


def _integrity_snapshot(connection: Connection) -> dict[str, int]:
    return {
        "orphan_prices": int(
            _scalar(
                connection,
                "SELECT count(*) FROM asset_prices p LEFT JOIN assets a ON a.id = p.asset_id WHERE a.id IS NULL",
            )
        ),
        "duplicate_prices": int(
            _scalar(
                connection,
                """
                SELECT count(*) FROM (
                    SELECT asset_id, timestamp
                      FROM asset_prices
                     GROUP BY asset_id, timestamp
                    HAVING count(*) > 1
                ) duplicated
                """,
            )
        ),
    }


def inspect(connection: Connection) -> dict[str, Any]:
    assets: dict[str, Any] = {}
    aliases: dict[str, Any] = {}
    legacy_prices: dict[str, Any] = {}
    official_prices: dict[str, Any] = {}
    for mapping in MAPPINGS:
        assets[str(mapping.legacy_id)] = _asset(connection, mapping.legacy_id)
        assets[str(mapping.canonical_id)] = _asset(connection, mapping.canonical_id)
        aliases[mapping.legacy_ticker] = _alias_snapshot(connection, mapping.legacy_ticker)
        legacy_prices[str(mapping.legacy_id)] = _price_snapshot(connection, mapping.legacy_id, LEGACY_SOURCE)
        official_prices[str(mapping.canonical_id)] = _price_snapshot(connection, mapping.canonical_id, OFFICIAL_SOURCE)
    return {
        "assets": assets,
        "aliases": aliases,
        "functional_references": _reference_counts(connection),
        "legacy_prices": legacy_prices,
        "official_prices": official_prices,
        "integrity": _integrity_snapshot(connection),
    }


def _validate_before(snapshot: dict[str, Any]) -> None:
    for mapping in MAPPINGS:
        legacy = snapshot["assets"][str(mapping.legacy_id)]
        canonical = snapshot["assets"][str(mapping.canonical_id)]
        expected_legacy = {"id": mapping.legacy_id, "ticker": mapping.legacy_ticker, "asset_type": ASSET_TYPE}
        expected_canonical = {"id": mapping.canonical_id, "ticker": mapping.canonical_ticker, "asset_type": ASSET_TYPE}
        if legacy != expected_legacy:
            raise TreasuryLegacyCleanupError(f"ativo legado divergente: {mapping.legacy_id}")
        if canonical != expected_canonical:
            raise TreasuryLegacyCleanupError(f"ativo canônico divergente: {mapping.canonical_id}")
        aliases = snapshot["aliases"][mapping.legacy_ticker]
        if aliases:
            raise TreasuryLegacyCleanupError(f"alias já existe ou conflita: {mapping.legacy_ticker}")
        legacy_prices = snapshot["legacy_prices"][str(mapping.legacy_id)]
        if legacy_prices["count"] != 2 or legacy_prices["enriched"] != 0:
            raise TreasuryLegacyCleanupError(f"conjunto de preços legado divergente: {mapping.legacy_id}")
        if Decimal(legacy_prices["min_close"]) != mapping.expected_close or Decimal(legacy_prices["max_close"]) != mapping.expected_close:
            raise TreasuryLegacyCleanupError(f"valor de preço legado divergente: {mapping.legacy_id}")
        official = snapshot["official_prices"][str(mapping.canonical_id)]
        if official["count"] < 743:
            raise TreasuryLegacyCleanupError(f"série oficial insuficiente: {mapping.canonical_id}")
    unexpected = {key: value for key, value in snapshot["functional_references"].items() if value}
    if unexpected:
        raise TreasuryLegacyCleanupError(f"referências funcionais inesperadas: {unexpected}")
    if snapshot["integrity"] != {"orphan_prices": 0, "duplicate_prices": 0}:
        raise TreasuryLegacyCleanupError("integridade inicial divergente")


def _validate_after(before: dict[str, Any], after: dict[str, Any]) -> None:
    for mapping in MAPPINGS:
        if after["assets"][str(mapping.legacy_id)] is not None:
            raise TreasuryLegacyCleanupError(f"ativo legado não removido: {mapping.legacy_id}")
        if after["assets"][str(mapping.canonical_id)] != before["assets"][str(mapping.canonical_id)]:
            raise TreasuryLegacyCleanupError(f"ativo canônico alterado: {mapping.canonical_id}")
        aliases = after["aliases"][mapping.legacy_ticker]
        if len(aliases) != 1 or aliases[0]["asset_id"] != mapping.canonical_id:
            raise TreasuryLegacyCleanupError(f"alias pós-operação divergente: {mapping.legacy_ticker}")
        if after["legacy_prices"][str(mapping.legacy_id)]["count"] != 0:
            raise TreasuryLegacyCleanupError(f"preços legados não removidos: {mapping.legacy_id}")
        if after["official_prices"][str(mapping.canonical_id)] != before["official_prices"][str(mapping.canonical_id)]:
            raise TreasuryLegacyCleanupError(f"série oficial alterada: {mapping.canonical_id}")
    if after["integrity"] != {"orphan_prices": 0, "duplicate_prices": 0}:
        raise TreasuryLegacyCleanupError("integridade final divergente")


def execute(
    connection: Connection,
    *,
    apply: bool = False,
    before_post_validation: Callable[[], None] | None = None,
) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc).isoformat()
    before = inspect(connection)

    already_applied = all(
        before["assets"][str(mapping.legacy_id)] is None
        and len(before["aliases"][mapping.legacy_ticker]) == 1
        and before["aliases"][mapping.legacy_ticker][0]["asset_id"] == mapping.canonical_id
        and before["legacy_prices"][str(mapping.legacy_id)]["count"] == 0
        for mapping in MAPPINGS
    )
    if already_applied:
        return {
            "schema_version": SCHEMA_VERSION,
            "mode": "apply" if apply else "dry-run",
            "status": "already-applied",
            "started_at": started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "before": before,
            "after": before,
            "planned": {"aliases": 0, "prices": 0, "assets": 0},
        }

    _validate_before(before)
    if not apply:
        return {
            "schema_version": SCHEMA_VERSION,
            "mode": "dry-run",
            "status": "validated",
            "started_at": started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "before": before,
            "after": None,
            "planned": {"aliases": 2, "prices": 4, "assets": 2},
        }

    for mapping in MAPPINGS:
        connection.execute(
            text(
                """
                INSERT INTO asset_aliases (asset_id, alias_ticker, asset_type, source_provider)
                VALUES (:asset_id, :alias_ticker, :asset_type, :source_provider)
                """
            ),
            {
                "asset_id": mapping.canonical_id,
                "alias_ticker": mapping.legacy_ticker,
                "asset_type": ASSET_TYPE,
                "source_provider": "treasury_legacy_cleanup.v1",
            },
        )
    deleted_prices = connection.execute(
        text("DELETE FROM asset_prices WHERE asset_id IN :legacy_ids AND source = :source"),
        {"legacy_ids": tuple(item.legacy_id for item in MAPPINGS), "source": LEGACY_SOURCE},
    ).rowcount
    deleted_assets = connection.execute(
        text("DELETE FROM assets WHERE id IN :legacy_ids"),
        {"legacy_ids": tuple(item.legacy_id for item in MAPPINGS)},
    ).rowcount
    if deleted_prices != 4 or deleted_assets != 2:
        raise TreasuryLegacyCleanupError("contagem de exclusão divergente; rollback obrigatório")
    if before_post_validation:
        before_post_validation()
    after = inspect(connection)
    _validate_after(before, after)
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "apply",
        "status": "applied",
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "before": before,
        "after": after,
        "planned": {"aliases": 2, "prices": 4, "assets": 2},
        "applied": {"aliases": 2, "prices": deleted_prices, "assets": deleted_assets},
    }
