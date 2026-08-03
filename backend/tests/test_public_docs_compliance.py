from pathlib import Path

import pytest


# Documentos que descrevem o produto e o estado operacional vigente devem
# permanecer neutros em relação a provedores. O CHANGELOG é deliberadamente
# excluído porque preserva o histórico técnico auditável de implementações já
# realizadas; reescrever esse registro apagaria contexto de decisões passadas.
CURRENT_PUBLIC_DOCUMENTS = (
    "README.md",
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


def _find_repository_root() -> Path | None:
    """Localiza a raiz somente quando os documentos públicos estão disponíveis.

    No CI o checkout completo contém README.md acima de ``backend``. Na imagem
    Docker do backend, cujo build context é ``backend/``, esses arquivos não são
    copiados e o teste deve ser explicitamente ignorado em vez de procurar em
    ``/README.md``.
    """

    for candidate in Path(__file__).resolve().parents:
        if all(
            (candidate / relative_path).is_file()
            for relative_path in CURRENT_PUBLIC_DOCUMENTS
        ):
            return candidate
    return None


def test_current_public_documents_do_not_expose_provider_names() -> None:
    repository_root = _find_repository_root()
    if repository_root is None:
        pytest.skip("Documentos públicos não estão incluídos na imagem isolada do backend")

    violations: list[str] = []

    for relative_path in CURRENT_PUBLIC_DOCUMENTS:
        document_path = repository_root / relative_path
        content = document_path.read_text(encoding="utf-8").lower()
        for provider_name in FORBIDDEN_PROVIDER_NAMES:
            if provider_name in content:
                violations.append(f"{relative_path}: {provider_name}")

    assert not violations, (
        "Nomes de provedores encontrados em documentos públicos atuais: "
        + ", ".join(violations)
    )
