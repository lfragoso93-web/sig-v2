"""Regressões da contração da materialização no pipeline de mercado."""
import ast
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
            materialize=True,
            commit=True,
        )

    run_backfill.assert_awaited_once_with(db, "PETR4", AssetType.ACAO)
    assert result.events_synced is True
    assert result.materialized == 0
    assert "materialization_disabled" in result.skipped_steps
    db.commit.assert_awaited_once()
