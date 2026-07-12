from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

PUBLIC_DOCUMENTS = (
    "README.md",
    "CHANGELOG.md",
    "ROADMAP_SPRINTS.md",
    "SUMARIO_EXECUTIVO.md",
    "GAPS_ANALISE_COMPLETA.md",
    "PLANO_ACAO_EXECUTAVEL.md",
    "MATRIZ_PRIORIZACAO.md",
)

FORBIDDEN_PROVIDER_NAMES = (
    "brapi",
    "alpha vantage",
    "yfinance",
    "tesouro transparente",
)


def test_public_documents_do_not_expose_provider_names() -> None:
    violations: list[str] = []

    for relative_path in PUBLIC_DOCUMENTS:
        document_path = REPOSITORY_ROOT / relative_path
        assert document_path.exists(), f"Documento público não encontrado: {relative_path}"

        content = document_path.read_text(encoding="utf-8").lower()
        for provider_name in FORBIDDEN_PROVIDER_NAMES:
            if provider_name in content:
                violations.append(f"{relative_path}: {provider_name}")

    assert not violations, (
        "Nomes de provedores encontrados em documentos públicos: "
        + ", ".join(violations)
    )
