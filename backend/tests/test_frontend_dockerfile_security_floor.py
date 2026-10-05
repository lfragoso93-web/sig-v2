from pathlib import Path


_FRONTEND_DOCKERFILE = (
    Path(__file__).resolve().parents[2] / "frontend" / "Dockerfile"
)


def test_frontend_runtime_enforces_fixed_alpine_security_floors() -> None:
    source = _FRONTEND_DOCKERFILE.read_text(encoding="utf-8")

    assert "apk upgrade --no-cache" in source
    assert "'libexpat>=2.8.5-r0'" in source
    assert "'pcre2>=10.49-r0'" in source
    assert source.index("apk upgrade --no-cache") < source.index("USER 101:101")
