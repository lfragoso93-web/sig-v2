from __future__ import annotations

from collections.abc import Iterable

from fastapi.routing import RouteContext, iter_route_contexts
from starlette.routing import BaseRoute


def iter_effective_route_contexts(routes: Iterable[BaseRoute]) -> list[RouteContext]:
    """Return effective route contexts across FastAPI's router tree.

    FastAPI 0.137+ keeps included routers as tree nodes in ``app.routes`` instead
    of flattening child routes into the top-level list. ``iter_route_contexts``
    is the supported traversal helper for resolving effective paths/methods.
    """
    return list(iter_route_contexts(list(routes)))


def http_method_path_pairs(routes: Iterable[BaseRoute]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for context in iter_effective_route_contexts(routes):
        path = context.path
        methods = context.methods or set()
        if not path:
            continue
        for method in methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            pairs.append((method, path))
    return pairs
