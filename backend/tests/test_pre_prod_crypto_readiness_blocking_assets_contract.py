import ast
from pathlib import Path

READINESS_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "cli"
    / "pre_prod_crypto_readiness_audit.py"
)


def test_readiness_exposes_nominal_blocking_assets() -> None:
    source = READINESS_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    run_function = next(
        node
        for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "_run"
    )
    return_node = next(
        node
        for node in ast.walk(run_function)
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict)
    )
    keys = {
        key.value
        for key in return_node.value.keys
        if isinstance(key, ast.Constant) and isinstance(key.value, str)
    }

    assert "blocking_assets" in keys
    assert "persisted_candidate_memberships" in keys
    assert "financially_certified_universe_size" in keys
    assert "crypto_financial_universe_ready" in keys
    assert "Asset.provider_status.in_(BLOCKING_STATUSES)" in source
    assert "FINANCIALLY_CERTIFIED_CRYPTO_STATUSES" in source
    assert "HISTORY_START_COMPLEMENT_UNAVAILABLE" in source
    assert "HISTORY_UNAVAILABLE" in source
    assert "Asset.ticker" in source
    assert "Asset.provider_symbol" in source
    assert "Asset.provider_attempts" in source
