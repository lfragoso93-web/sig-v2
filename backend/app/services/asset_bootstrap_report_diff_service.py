"""Comparação offline de relatórios do bootstrap canônico de ativos."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AssetBootstrapReportDiff:
    equivalent: bool
    changed_fields: tuple[str, ...]
    changed_capabilities: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "equivalent": self.equivalent,
            "changed_fields": list(self.changed_fields),
            "changed_capabilities": list(self.changed_capabilities),
        }


def compare_asset_bootstrap_reports(
    before: dict[str, object],
    after: dict[str, object],
) -> AssetBootstrapReportDiff:
    """Compara dois relatórios serializados sem acessar banco ou providers."""

    changed_fields = tuple(
        field
        for field in ("ticker", "asset_type", "ok", "coverage")
        if before.get(field) != after.get(field)
    )

    before_capabilities = _capability_map(before)
    after_capabilities = _capability_map(after)
    changed_capabilities = tuple(
        name
        for name in sorted(set(before_capabilities) | set(after_capabilities))
        if before_capabilities.get(name) != after_capabilities.get(name)
    )

    return AssetBootstrapReportDiff(
        equivalent=not changed_fields and not changed_capabilities,
        changed_fields=changed_fields,
        changed_capabilities=changed_capabilities,
    )


def _capability_map(report: dict[str, object]) -> dict[str, object]:
    raw_capabilities = report.get("capabilities", [])
    if not isinstance(raw_capabilities, list):
        raise ValueError("capabilities must be a list")

    mapped: dict[str, object] = {}
    for item in raw_capabilities:
        if not isinstance(item, dict):
            raise ValueError("capability entry must be an object")
        name = item.get("capability")
        if not isinstance(name, str) or not name:
            raise ValueError("capability name is required")
        if name in mapped:
            raise ValueError(f"duplicate capability: {name}")
        mapped[name] = item
    return mapped
