from __future__ import annotations

from typing import Any


def normalize_crypto_catalog_items(raw_items: Any) -> list[dict]:
    """Retorna somente itens-mapa válidos do catálogo de cripto da BRAPI."""
    if not isinstance(raw_items, list):
        return []
    return [item for item in raw_items if isinstance(item, dict)]
