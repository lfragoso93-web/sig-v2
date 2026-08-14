"""Regressões da contração da materialização no pipeline de mercado."""
import ast
import inspect
from dataclasses import asdict
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.models.asset import AssetType
from app.services.asset_market_pipeline_service import sync_asset_market_data


@pytest.mark.parametrize(
    "service_path",
    [
        Path("app/services/asset_onboarding_service.py"),
        Path("app/services/asset_seed_service.py"),
        Path("app/services/dividend_history_seed_service.py"),
        Path("app/services/market_pipeline_batch_service.py"),
        Path("app/cli/run_market_pipeline.py"),
        Path("app/cli/run_market_pipeline_batch.py"),
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


@pytest.mark.parametrize(
    "cli_path",
    [
        Path("app/cli/run_market_pipeline.py"),
        Path("app/cli/run_market_pipeline_batch.py"),
    ],
)
def test_cli_de_mercado_nao_expoe_opcao_de_materializacao(
    cli_path: Path,
) -> None:
    source_path = Path(__file__).parents[1] / cli_path
    source = source_path.read_text(encoding="utf-8")

    assert "--skip-materialize" not in source


def test_cli_legada_de_proventos_nao_existe() -> None:
    cli_path = Path(__file__).parents[1] / "app/cli/run_proventos_sync.py"

    assert not cli_path.exists()


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


@pytest.mark.asyncio
async def test_pipeline_sincroniza_eventos_sem_materializar_direitos() -> None:
    db = Mock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.rollback = AsyncMock()
    asset = Mock()

    with (
        patch(
            "app.services.asset_market_pipeline_service._get_or_create_asset",
            new=AsyncMock(return_value=(asset, False, False)),
        ),
        patch(
            "app.services.asset_market_pipeline_service.run_backfill",
            new=AsyncMock(),
        ) as run_backfill,
    ):
        result = await sync_asset_market_data(
            db=db,
            ticker="PETR4",
            asset_type=AssetType.ACAO,
            sync_prices=False,
            sync_logo=False,
            sync_events=True,
            commit=True,
        )

    run_backfill.assert_awaited_once_with(db, "PETR4", AssetType.ACAO)
    assert result.events_synced is True
    assert "materialize" not in inspect.signature(sync_asset_market_data).parameters
    assert "materialized" not in asdict(result)
    assert all("materializ" not in step for step in result.skipped_steps)
    db.commit.assert_awaited_once()
