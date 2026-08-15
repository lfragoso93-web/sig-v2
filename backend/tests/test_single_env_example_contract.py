"""Protege o contrato único de configuração distribuído na raiz do projeto."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_root_env_example_is_the_only_distributed_example() -> None:
    assert (ROOT / ".env.example").is_file()
    assert not (ROOT / "backend" / ".env.example").exists()
