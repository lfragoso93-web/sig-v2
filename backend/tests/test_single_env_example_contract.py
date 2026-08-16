"""Protege o contrato único de configuração distribuído na raiz do projeto."""
from pathlib import Path

import pytest


BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent


def test_backend_does_not_ship_parallel_env_example() -> None:
    assert not (BACKEND / ".env.example").exists()


def test_root_env_example_is_the_only_distributed_example() -> None:
    root_env = ROOT / ".env.example"
    if not root_env.is_file():
        pytest.skip(".env.example da raiz indisponivel na imagem backend isolada")

    assert root_env.is_file()
    assert not (BACKEND / ".env.example").exists()
