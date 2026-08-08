from collections import Counter

from fastapi.routing import APIRoute

from app.main import app


def test_app_has_no_duplicate_http_method_path_pairs() -> None:
    pairs: list[tuple[str, str]] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or set():
            if method in {"HEAD", "OPTIONS"}:
                continue
            pairs.append((method, route.path))

    counts = Counter(pairs)
    duplicates = sorted(pair for pair, count in counts.items() if count > 1)
    assert duplicates == []
