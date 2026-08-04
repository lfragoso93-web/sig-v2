"""Testes da CLI interna da apuração anual canônica."""

import argparse
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.cli.irpf_annual_assessment import _main


@pytest.mark.asyncio
async def test_cli_emits_contract_and_rolls_back(capsys: pytest.CaptureFixture[str]) -> None:
    session = AsyncMock()
    context = AsyncMock()
    context.__aenter__.return_value = session
    context.__aexit__.return_value = None
    contract = MagicMock()
    contract.to_dict.return_value = {
        "schema_version": "irpf-annual-assessment.v1",
        "portfolio_id": 7,
        "year": 2024,
    }

    with (
        patch(
            "app.cli.irpf_annual_assessment.AsyncSessionLocal",
            return_value=context,
        ),
        patch(
            "app.cli.irpf_annual_assessment.build_irpf_annual_assessment",
            new=AsyncMock(return_value=contract),
        ) as build,
    ):
        exit_code = await _main(SimpleNamespace(portfolio_id=7, year=2024))

    assert exit_code == 0
    build.assert_awaited_once_with(session, portfolio_id=7, year=2024)
    session.rollback.assert_awaited_once()
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == "irpf-annual-assessment.v1"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (argparse.Namespace(portfolio_id=0, year=2024), "portfolio-id deve ser positivo"),
        (argparse.Namespace(portfolio_id=1, year=1899), "ano fiscal inválido"),
    ],
)
async def test_cli_rejects_invalid_arguments(
    arguments: argparse.Namespace,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        await _main(arguments)
