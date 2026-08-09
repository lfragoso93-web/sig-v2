from __future__ import annotations

from pathlib import Path


def test_treasury_symbol_resolution_does_not_seed_provider_on_demand() -> None:
    source = Path("app/services/treasury_catalog_service.py").read_text(encoding="utf-8")

    start = source.index("async def resolve_treasury_symbol")
    resolver_source = source[start:]

    assert "await seed_treasury_assets(" not in resolver_source
    assert "catálogo persistido" in resolver_source
