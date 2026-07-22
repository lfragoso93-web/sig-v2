"""Regressões da migração Pydantic ConfigDict da Issue #186."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from app.core.config import Settings
from app.routers.assets import AssetListItem
from app.schemas.asset import AssetRead
from app.schemas.audit_log import AuditLogResponse
from app.schemas.dividend import DividendRead
from app.schemas.portfolio import ClassTargetRead, ClassTargetWithCurrent, PortfolioRead
from app.schemas.treasury import TreasuryPositionResponse


APP_ROOT = Path(__file__).resolve().parents[1] / "app"


def _legacy_config_classes() -> set[str]:
    found: set[str] = set()

    for path in APP_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        relative_path = path.relative_to(APP_ROOT).as_posix()

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            for child in node.body:
                if isinstance(child, ast.ClassDef) and child.name == "Config":
                    found.add(f"{relative_path}:{node.name}.Config")

    return found


def test_backend_has_no_legacy_pydantic_config_classes() -> None:
    assert _legacy_config_classes() == set()


def test_settings_preserves_environment_configuration() -> None:
    assert Settings.model_config["env_file"] == ".env"
    assert Settings.model_config["case_sensitive"] is True


def test_portfolio_schemas_preserve_from_attributes() -> None:
    now = datetime.now(timezone.utc)

    portfolio = PortfolioRead.model_validate(
        SimpleNamespace(id=1, user_id=2, name="Principal", description=None, created_at=now)
    )
    target = ClassTargetRead.model_validate(
        SimpleNamespace(id=3, portfolio_id=1, asset_type="FII", target_pct=Decimal("20"))
    )
    current = ClassTargetWithCurrent.model_validate(
        SimpleNamespace(
            asset_type="FII",
            label="Fundos Imobiliarios",
            target_pct=20.0,
            current_pct=18.5,
            delta_pct=-1.5,
            color="#000000",
        )
    )

    assert portfolio.name == "Principal"
    assert target.target_pct == Decimal("20")
    assert current.delta_pct == -1.5


def test_audit_log_schema_preserves_from_attributes() -> None:
    now = datetime.now(timezone.utc)
    audit_log = AuditLogResponse.model_validate(
        SimpleNamespace(
            id=1,
            user_id=2,
            action="CREATE",
            resource_type="portfolio",
            resource_id=3,
            portfolio_id=3,
            ip_address=None,
            user_agent=None,
            status="SUCCESS",
            error_message=None,
            created_at=now,
        )
    )

    assert audit_log.resource_type == "portfolio"
    assert audit_log.created_at == now


def test_additional_read_schemas_preserve_from_attributes() -> None:
    asset = AssetRead.model_validate(
        SimpleNamespace(
            id=1,
            ticker="PETR4",
            name="Petrobras",
            asset_type="ACAO",
            sector=None,
            currency="BRL",
            logo_url=None,
            last_price=30.0,
        )
    )
    dividend = DividendRead.model_validate(
        SimpleNamespace(
            id=2,
            ticker="PETR4",
            ex_date="2026-07-01",
            payment_date="2026-07-15",
            value_per_unit=1.25,
            dividend_type="DIVIDENDO",
            total_received=12.5,
            portfolio_id=1,
        )
    )
    treasury = TreasuryPositionResponse.model_validate(
        SimpleNamespace(
            id=3,
            portfolio_id=1,
            brapi_name="Tesouro Selic 2029",
            ticker="TESOURO-SELIC-2029",
            purchase_price=100.0,
            quantity=1.0,
            invested_value=100.0,
        )
    )
    listed_asset = AssetListItem.model_validate(
        SimpleNamespace(
            id=4,
            ticker="MXRF11",
            name="Maxi Renda",
            asset_type="FII",
            last_price=10.0,
            last_price_updated_at=None,
        )
    )

    assert asset.ticker == "PETR4"
    assert dividend.total_received == 12.5
    assert treasury.invested_value == 100.0
    assert listed_asset.asset_type == "FII"
