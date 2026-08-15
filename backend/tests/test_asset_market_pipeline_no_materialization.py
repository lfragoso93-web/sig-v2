"""Regressões da contração da materialização no pipeline de mercado."""
import ast
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "service_path",
    [
        Path("app/services/asset_seed_service.py"),
        Path("app/services/dividend_history_seed_service.py"),
        Path("app/core/scheduler.py"),
    ],
)
def test_callers_de_aplicacao_nao_solicitam_materializacao(
    service_path: Path,
) -> None:
    source_path = Path(__file__).parents[1] / service_path
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    assert all(
        "materialize" not in {keyword.arg for keyword in call.keywords}
        for call in calls
    )


def test_cli_legada_de_proventos_nao_existe() -> None:
    cli_path = Path(__file__).parents[1] / "app/cli/run_proventos_sync.py"

    assert not cli_path.exists()


def test_asset_onboarding_legado_nao_existe() -> None:
    service_path = (
        Path(__file__).parents[1]
        / "app/services/asset_onboarding_service.py"
    )

    assert not service_path.exists()


@pytest.mark.parametrize(
    "path",
    [
        Path("app/services/market_pipeline_batch_service.py"),
        Path("app/cli/run_market_pipeline.py"),
        Path("app/cli/run_market_pipeline_batch.py"),
    ],
)
def test_portas_manuais_legadas_de_mercado_nao_existem(path: Path) -> None:
    assert not (Path(__file__).parents[1] / path).exists()


def test_seed_historico_nao_importa_materializador() -> None:
    source_path = (
        Path(__file__).parents[1]
        / "app/services/dividend_history_seed_service.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }

    assert "materialize_asset_dividends" not in imported_names


@pytest.mark.parametrize(
    "path",
    [
        Path("app/services/asset_seed_service.py"),
    ],
)
def test_pipeline_de_mercado_nao_expoe_porta_de_eventos(path: Path) -> None:
    source = (Path(__file__).parents[1] / path).read_text(encoding="utf-8")

    assert "sync_events" not in source
    assert "events_synced" not in source
    assert "--skip-events" not in source
    assert "dividend_backfill_service" not in source


def test_pipeline_legado_de_mercado_nao_existe() -> None:
    path = (
        Path(__file__).parents[1]
        / "app/services/asset_market_pipeline_service.py"
    )

    assert not path.exists()
