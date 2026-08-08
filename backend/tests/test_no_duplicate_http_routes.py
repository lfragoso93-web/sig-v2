from collections import Counter

from app.main import app
from tests.route_tree_helpers import http_method_path_pairs


def test_app_has_no_duplicate_http_method_path_pairs() -> None:
    pairs = http_method_path_pairs(app.routes)
    counts = Counter(pairs)
    duplicates = sorted(pair for pair, count in counts.items() if count > 1)
    assert duplicates == []
