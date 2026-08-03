"""Regression guard for canonical-only pre-production dividend seed."""

from __future__ import annotations

import ast
from pathlib import Path

SERVICES_PATH = Path(__file__).resolve().parents[2] / "app" / "services"
SERVICE_PATH = SERVICES_PATH / "pre_prod_dividends_seed_service.py"
CONTRACT_PATH = SERVICES_PATH / "pre_prod_dividends_seed_contract.py"
CLI_PATH = (
    Path(__file__).resolve().parents[2] / "app" / "cli" / "pre_prod_dividends_seed.py"
)


def test_seed_runner_and_cli_do_not_import_or_call_materialization() -> None:
    for path in (SERVICE_PATH, CLI_PATH):
        source = path.read_text(encoding="utf-8")
        assert "pre_prod_dividends_seed_materialization" not in source
        assert "materialize_portfolio_dividends_strict" not in source
        assert "portfolio_materialization" not in source

    service_tree = ast.parse(SERVICE_PATH.read_text(encoding="utf-8"))
    runner = next(
        node
        for node in service_tree.body
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name == "run_pre_prod_dividends_seed"
    )
    assert "materialization_runner" not in {
        argument.arg for argument in runner.args.kwonlyargs
    }


def test_seed_write_boundary_is_canonical_only() -> None:
    contract_tree = ast.parse(CONTRACT_PATH.read_text(encoding="utf-8"))
    assignment = next(
        node
        for node in contract_tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "DIVIDENDS_SEED_WRITE_TABLES"
            for target in node.targets
        )
    )

    assert ast.literal_eval(assignment.value) == ("asset_dividends",)


def test_v2_contract_and_inspection_have_no_legacy_materialization_surface() -> None:
    contract_source = CONTRACT_PATH.read_text(encoding="utf-8")
    inspection_source = (
        SERVICES_PATH / "pre_prod_dividends_seed_inspection.py"
    ).read_text(encoding="utf-8")
    inspection_tree = ast.parse(inspection_source)
    imported_modules = {
        node.module
        for node in ast.walk(inspection_tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }

    assert 'DIVIDENDS_SEED_SCHEMA_VERSION = "pre-prod-dividends-seed.v2"' in (
        contract_source
    )
    assert "materialization:" not in contract_source
    assert "app.models.dividend" not in imported_modules
    assert "app.models.transaction" not in imported_modules
    assert not (SERVICES_PATH / "pre_prod_dividends_seed_materialization.py").exists()
