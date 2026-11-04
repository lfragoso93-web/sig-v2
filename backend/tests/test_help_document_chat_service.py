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


@pytest.mark.parametrize("question", ["", "  ", "oi", "x" * 501])
def test_help_chat_question_has_bounded_nonempty_length(question: str) -> None:
    with pytest.raises(ValidationError):
        HelpChatQuestionRequest(question=question)


def test_help_chat_question_trims_outer_whitespace() -> None:
    request = HelpChatQuestionRequest(question="  Como calculo o TWR?  ")

    assert request.question == "Como calculo o TWR?"
