from __future__ import annotations

from pathlib import Path

import pytest


WRAPPER_NAME = "compare_pre_prod_macro_seed.ps1"


def _find_wrapper() -> Path | None:
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "scripts" / WRAPPER_NAME
        if candidate.exists():
            return candidate
    return None


def test_wrapper_persists_validated_comparison_artifact():
    wrapper = _find_wrapper()
    if wrapper is None:
        pytest.skip("checkout backend não inclui o diretório scripts")

    content = wrapper.read_text(encoding="utf-8")

    assert "macro-seed-compare.json" in content
    assert "pre-prod-macro-seed-compare.v1" in content
    assert "compare_macro_seed_files" in content
    assert 'encoding="utf-8"' in content
    assert "Test-Path -LiteralPath $OutputPath" in content
    assert "A evidência de comparação já existe" in content
    assert "$Payload.ok -ne $true" in content
    assert "$ExitCode -ne 0" in content
    assert "ConvertFrom-Json" in content
