from pathlib import Path

from pydantic import ValidationError
import pytest

from app.schemas.help_chat import HelpChatQuestionRequest
from app.services.help_document_chat_service import HelpDocumentChatService


def test_help_chat_retrieves_a_cited_passage_from_allowlisted_document(tmp_path: Path) -> None:
    (tmp_path / "DOCUMENTACAO_DO_SISTEMA.md").write_text(
        "# Manual\n\n## Snapshot oficial\n\n"
        "O snapshot oficial da carteira é diário às 21h, inclusive sábados, domingos e feriados.",
        encoding="utf-8",
    )

    result = HelpDocumentChatService(tmp_path).answer(
        "Como funciona o snapshot oficial diário aos sábados e domingos?"
    )

    assert result.sources
    assert result.sources[0].document == "Manual do sistema"
    assert result.sources[0].section == "Snapshot oficial"
    assert "sábados, domingos" in result.sources[0].excerpt


def test_help_chat_does_not_search_non_allowlisted_documents(tmp_path: Path) -> None:
    (tmp_path / "DOCUMENTACAO_DO_SISTEMA.md").write_text(
        "## Sistema\n\nCarteiras registram transações e posições.",
        encoding="utf-8",
    )
    (tmp_path / "REAL_DATA_CERTIFICATION_RUNBOOK.md").write_text(
        "## Segredo interno\n\nChave confidencial para produção.",
        encoding="utf-8",
    )

    result = HelpDocumentChatService(tmp_path).answer("Qual é a chave confidencial de produção?")

    assert result.sources == []
    assert "Não encontrei" in result.answer


def test_help_chat_returns_no_answer_when_documentation_has_no_match(tmp_path: Path) -> None:
    (tmp_path / "DOCUMENTACAO_DO_SISTEMA.md").write_text(
        "## Visão geral\n\nO sistema acompanha carteiras de investimentos.",
        encoding="utf-8",
    )

    result = HelpDocumentChatService(tmp_path).answer("Como configurar um telescópio espacial?")

    assert result.sources == []
    assert "Tente reformular" in result.answer


def test_help_chat_excerpt_keeps_the_matching_passage_when_it_is_late_in_section(
    tmp_path: Path,
) -> None:
    filler = "A simulacao usa premissas constantes e nao inclui marcacao a mercado. " * 22
    (tmp_path / "TOOLS_CALCULATORS.md").write_text(
        "# Ferramentas\n\n## Simulador\n\n"
        "O simulador calcula o valor futuro com premissas fixas. "
        f"{filler}"
        "O simulador nao modela resgate antecipado.",
        encoding="utf-8",
    )

    result = HelpDocumentChatService(tmp_path).answer(
        "O simulador considera resgate antecipado?"
    )

    assert result.sources
    assert "nao modela resgate antecipado" in result.sources[0].excerpt.casefold()
    assert len(result.sources[0].excerpt) <= 700


def test_help_chat_excludes_superseded_corporate_action_status_sections(
    tmp_path: Path,
) -> None:
    (tmp_path / "CORPORATE_ACTIONS.md").write_text(
        "# Eventos corporativos\n\n"
        "## Liquidação de frações\n\n"
        "A liquidação de frações é apresentada quando o evento confirmado gera saldo fracionário.\n\n"
        "## Estado de publicação — 16/10/2026\n\n"
        "KLBN11 permanece pendente em conflito e ainda precisa de validação.\n\n"
        "## Próximos blocos\n\n"
        "KLBN11 continua pendente até a próxima entrega.\n\n"
        "## Conclusão da reconciliação KLBN11 — 21/10/2026\n\n"
        "A reconciliação KLBN11 foi concluída e a issue foi fechada.",
        encoding="utf-8",
    )

    result = HelpDocumentChatService(tmp_path).answer(
        "KLBN11 permanece pendente em conflito?"
    )

    assert result.sources == []
    assert "Tente reformular" in result.answer


def test_help_chat_answers_the_suggested_twr_question_from_current_documentation() -> None:
    repository_docs = Path(__file__).resolve().parents[2] / "docs"
    document_root = (
        repository_docs
        if (repository_docs / "snapshots.md").is_file()
        and (repository_docs / "CORPORATE_ACTIONS.md").is_file()
        else Path(__file__).resolve().parents[1] / "help_docs"
    )

    result = HelpDocumentChatService(document_root).answer(
        "Como é calculado o TWR acumulado?"
    )

    assert result.sources
    assert any(source.section == "Retorno acumulado" for source in result.sources)
    assert any("accumulated_return_pct" in source.excerpt for source in result.sources)


@pytest.mark.parametrize("question", ["", "  ", "oi", "x" * 501])
def test_help_chat_question_has_bounded_nonempty_length(question: str) -> None:
    with pytest.raises(ValidationError):
        HelpChatQuestionRequest(question=question)


def test_help_chat_question_trims_outer_whitespace() -> None:
    request = HelpChatQuestionRequest(question="  Como calculo o TWR?  ")

    assert request.question == "Como calculo o TWR?"


def test_help_chat_suggests_routes_for_navigation(tmp_path: Path) -> None:
    (tmp_path / "rentabilidade.md").write_text(
        "# Rentabilidade\n\n## TWR\n\nO TWR mede o desempenho sem aportes.",
        encoding="utf-8",
    )
    result = HelpDocumentChatService(tmp_path).answer(
        "Como funciona o TWR e a rentabilidade?"
    )
    assert result.sources
    assert any(
        route.path == "/carteira/rentabilidade"
        for route in result.suggested_routes
    )


@pytest.mark.asyncio
async def test_help_chat_answer_async_synthesizes_with_gemini(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import httpx
    from app.core.config import settings

    (tmp_path / "DOCUMENTACAO_DO_SISTEMA.md").write_text(
        "# Manual\n\n## Importação\n\nÉ possível importar via arquivo CSV.",
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-gemini-key")

    mock_gemini_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": "Você pode importar transações via CSV."
                        }
                    ]
                }
            }
        ]
    }

    captured_requests = []

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, **kwargs):
            captured_requests.append((url, kwargs))
            return httpx.Response(
                200,
                json=mock_gemini_response,
                request=httpx.Request("POST", url),
            )

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    service = HelpDocumentChatService(tmp_path)
    res = await service.answer_async("Como importar arquivo CSV?")
    assert res.mode == "llm"
    assert "CSV" in res.answer
    assert res.sources
    assert len(captured_requests) == 1
    req_url, req_kwargs = captured_requests[0]
    assert "key=" not in str(req_url)
    assert req_kwargs["headers"]["x-goog-api-key"] == "fake-gemini-key"


@pytest.mark.asyncio
async def test_help_chat_answer_async_falls_back_when_llm_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import httpx
    from app.core.config import settings

    (tmp_path / "DOCUMENTACAO_DO_SISTEMA.md").write_text(
        "# Manual\n\n## Transações\n\nTransações registram compras e vendas.",
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-gemini-key")

    class FailingAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, **kwargs):
            raise RuntimeError("API timeout or network failure")

    monkeypatch.setattr(httpx, "AsyncClient", FailingAsyncClient)

    service = HelpDocumentChatService(tmp_path)
    res = await service.answer_async("Como registrar transações?")
    assert res.mode == "deterministic"
    assert res.sources
    assert "Encontrei estes trechos" in res.answer


def test_help_chat_uses_backend_help_docs_and_excludes_engineering_jargon() -> None:
    from app.services.help_document_chat_service import _default_document_root
    root = _default_document_root()
    assert root.name == "help_docs"
    assert root.is_dir()

    service = HelpDocumentChatService(root)
    assert len(service._chunks) >= 50

    # Test answer on IRPF
    res_irpf = service.answer("Como funciona a isenção de 20 mil para ações no IRPF?")
    assert res_irpf.sources
    assert any("20.000" in s.excerpt for s in res_irpf.sources)

    # Test answer on CSV import
    res_csv = service.answer("Como importar transações por planilha CSV?")
    assert res_csv.sources
    assert any("csv" in s.excerpt.lower() for s in res_csv.sources)

    # Test answer on 2FA
    res_2fa = service.answer("Como ativar a autenticação de dois fatores 2FA?")
    assert res_2fa.sources
    assert any("totp" in s.excerpt.lower() or "autenticador" in s.excerpt.lower() for s in res_2fa.sources)

    # Ensure no citations in the entire corpus contain unwanted engineering jargon
    unwanted = ["stable-15jun", "pull request", "alembic", "issue #", "dockerfile"]
    for chunk in service._chunks:
        chunk_lower = chunk.text.lower()
        for term in unwanted:
            assert term not in chunk_lower, f"Unwanted term '{term}' found in {chunk.document} section '{chunk.section}'"
