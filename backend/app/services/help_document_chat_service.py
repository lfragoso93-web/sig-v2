from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
import logging
import math
from pathlib import Path
import re
import unicodedata

import httpx

from app.core.config import settings
from app.schemas.help_chat import (
    HelpChatResponse,
    HelpChatRouteSuggestion,
    HelpChatSource,
)

logger = logging.getLogger(__name__)

_ALLOWED_DOCUMENTS = (
    ("DOCUMENTACAO_DO_SISTEMA.md", "Manual do sistema"),
    ("rentabilidade.md", "Rentabilidade"),
    ("TOOLS_CALCULATORS.md", "Calculadoras e simuladores"),
    ("snapshots.md", "Snapshots e TWR"),
    ("GOALS_AND_ANALYSIS_CONTRACT.md", "Metas e análise de carteira"),
    ("CORPORATE_ACTIONS.md", "Eventos corporativos"),
)
_WORD_PATTERN = re.compile(r"[a-z0-9]{3,}")
_HEADING_PATTERN = re.compile(r"^(#{1,4})\s+(.+?)\s*#*\s*$", re.MULTILINE)
_STOP_WORDS = frozenset(
    (
        "a o as os um uma uns umas de da do das dos em no na nos nas por para "
        "com sem que como qual quais quando onde porque e ou se ao aos pelo "
        "pela pelos pelas sua seu suas seus isso esta este esse essa isto "
        "mais menos muito muita sobre entre desde ate ser ter pode podem "
        "sistema carteira dados voce usuario usar do da faz fazer sao foi"
    ).split()
)
_NO_MATCH_ANSWER = (
    "Não encontrei uma resposta suficiente nos documentos disponíveis. "
    "Tente reformular a pergunta ou consulte as perguntas frequentes."
)
_CORPORATE_ACTION_SECTIONS = frozenset(
    {
        "objetivo",
        "arquitetura canonica",
        "fontes",
        "convencao de fator",
        "liquidacao de fracoes",
        "idempotencia e auditoria",
        "candidatos cross-provider",
        "seguranca operacional",
        "avisos de eventos corporativos futuros",
    }
)

_ROUTE_DEFINITIONS = (
    (
        ("patrimonio", "posicao", "posicoes", "custo", "saldo", "ativos"),
        "Patrimônio",
        "/carteira/patrimonio",
        "Posições detalhadas, alocação e saldo consolidado",
    ),
    (
        ("rentabilidade", "twr", "retorno", "benchmark", "ibov", "cdi"),
        "Rentabilidade",
        "/carteira/rentabilidade",
        "Rentabilidade histórica ponderada pelo tempo (TWR)",
    ),
    (
        (
            "transacao",
            "transacoes",
            "lancamento",
            "compra",
            "venda",
            "taxa",
            "custos",
            "aporte",
        ),
        "Transações",
        "/carteira/transacoes",
        "Administração e lançamento de operações (Alt+N)",
    ),
    (
        (
            "provento",
            "proventos",
            "dividendo",
            "dividendos",
            "jcp",
            "rendimento",
        ),
        "Proventos",
        "/carteira/proventos",
        "Acompanhamento de proventos recebidos e provisionados",
    ),
    (
        ("meta", "metas", "alocacao", "objetivo"),
        "Metas",
        "/carteira/metas",
        "Alocação alvo por classe e acompanhamento de metas",
    ),
    (
        ("analise", "rebalanceamento", "concentracao", "score"),
        "Análise e IA",
        "/carteira/analise",
        "Diagnóstico da carteira e sugestões de rebalanceamento",
    ),
    (
        ("irpf", "imposto", "darf", "tributacao", "declaracao"),
        "IRPF",
        "/carteira/irpf",
        "Apuração de resultados e apoio para declaração",
    ),
    (
        ("calculadora", "juros", "rendimentos", "simulacao"),
        "Calculadora de Rendimentos",
        "/carteira/ferramentas/rendimentos",
        "Simulação de juros compostos e aportes regulares",
    ),
    (
        ("renda fixa", "cdb", "lci", "lca", "simulador rf"),
        "Simulador de Renda Fixa",
        "/carteira/ferramentas/renda-fixa",
        "Comparador de taxas e prazos de títulos de renda fixa",
    ),
    (
        ("comparar", "comparador", "multiplos", "indicadores"),
        "Comparador de Ativos",
        "/carteira/ferramentas/comparador",
        "Comparação lado a lado de múltiplos e histórico",
    ),
)


@dataclass(frozen=True)
class _DocumentChunk:
    document: str
    section: str
    text: str
    tokens: tuple[str, ...]


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )


def _tokens(value: str) -> tuple[str, ...]:
    return tuple(
        token
        for token in _WORD_PATTERN.findall(_normalize(value))
        if token not in _STOP_WORDS
    )


def _clean_markdown(value: str) -> str:
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    cleaned = re.sub(r"```[^\n]*\n?(.*?)```", r"\1", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"[`*~]", "", cleaned)
    cleaned = re.sub(
        r"^\s*[-|>#*]+\s*", "", cleaned, flags=re.MULTILINE
    )
    cleaned = re.sub(r"\|", " · ", cleaned)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def _split_paragraphs(text: str, max_chars: int = 1500) -> list[str]:
    paragraphs = [
        part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()
    ]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(
                paragraph[index: index + max_chars]
                for index in range(0, len(paragraph), max_chars)
            )
            continue
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) > max_chars:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def _is_searchable_section(filename: str, section: str) -> bool:
    normalized = _normalize(section)
    if normalized.startswith(
        ("pendencias", "roadmap", "historico", "diagnostico historico")
    ):
        return False
    if filename == "CORPORATE_ACTIONS.md":
        return normalized in _CORPORATE_ACTION_SECTIONS
    return True


def _relevant_excerpt(
    text: str, query_tokens: set[str], max_chars: int = 700
) -> str:
    """Keep the strongest matching passage inside the displayed citation."""
    matches = [
        (match.start(), match.end())
        for match in re.finditer(r"\w+", text, flags=re.UNICODE)
        if _normalize(match.group(0)) in query_tokens
    ]
    if not matches or len(text) <= max_chars:
        return text[:max_chars].strip()

    left = 0
    best_window = matches[0]
    best_count = 0
    for right, match in enumerate(matches):
        while match[1] - matches[left][0] > max_chars:
            left += 1
        count = right - left + 1
        if count > best_count:
            best_count = count
            best_window = (matches[left][0], match[1])

    context_before = min(180, max_chars - (best_window[1] - best_window[0]))
    start = max(0, best_window[0] - context_before)
    end = min(len(text), start + max_chars)
    if end == len(text):
        start = max(0, end - max_chars)
    elif start > 0:
        next_space = text.find(" ", start)
        if next_space != -1 and next_space < best_window[0]:
            start = next_space + 1
            end = min(len(text), start + max_chars)
    if end < len(text):
        previous_space = text.rfind(" ", start, end)
        if previous_space > best_window[1]:
            end = previous_space
    return text[start:end].strip()


def _suggest_routes(
    question: str, sources: list[HelpChatSource]
) -> list[HelpChatRouteSuggestion]:
    source_text = " ".join(
        f"{s.document} {s.section} {s.excerpt}" for s in sources
    )
    corpus = _normalize(f"{question} {source_text}")
    suggestions: list[HelpChatRouteSuggestion] = []
    seen_paths: set[str] = set()

    for keywords, label, path, description in _ROUTE_DEFINITIONS:
        if any(kw in corpus for kw in keywords):
            if path not in seen_paths:
                suggestions.append(
                    HelpChatRouteSuggestion(
                        label=label,
                        path=path,
                        description=description,
                    )
                )
                seen_paths.add(path)
                if len(suggestions) >= 3:
                    break
    return suggestions


async def _synthesize_answer_with_llm(
    question: str,
    sources: list[HelpChatSource],
) -> str | None:
    if not sources:
        return None

    context_blocks = []
    for idx, s in enumerate(sources, start=1):
        context_blocks.append(
            f"[{idx}] {s.document} | {s.section}\n{s.excerpt}"
        )
    context_text = "\n\n".join(context_blocks)

    system_instruction = (
        "Você é o Assistente Oficial do SGI v2 (Sistema de Gestão de "
        "Investimentos). Seu papel é responder dúvidas de forma concisa, "
        "educada e precisa em Português do Brasil.\n\n"
        "REGRAS:\n"
        "1. Baseie sua resposta EXCLUSIVAMENTE nos trechos de documentação "
        "oficial fornecidos no contexto.\n"
        "2. Seja direto e objetivo, explicando com clareza o funcionamento ou "
        "o cálculo questionado.\n"
        "3. Se a informação não constar nos trechos fornecidos, declare com "
        "clareza que o tema não está detalhado na documentação oficial "
        "disponível.\n"
        "4. Não invente dados de mercado, rentabilidades ou parâmetros "
        "fictícios."
    )

    user_prompt = (
        f"{system_instruction}\n\n"
        f"--- CONTEXTO DA DOCUMENTAÇÃO OFICIAL ---\n{context_text}\n\n"
        f"--- PERGUNTA DO USUÁRIO ---\n{question}\n\n"
        "Resposta:"
    )

    gemini_key = getattr(settings, "GEMINI_API_KEY", None)
    if gemini_key:
        try:
            model = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent"
            )
            headers = {"x-goog-api-key": gemini_key}
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": user_prompt}],
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 800,
                },
            }
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get(
                            "parts", []
                        )
                        if parts and "text" in parts[0]:
                            text = parts[0]["text"].strip()
                            if text:
                                return text
                logger.warning(
                    "Gemini API returned status %s: %s",
                    resp.status_code,
                    resp.text[:200],
                )
        except Exception as exc:
            logger.warning(
                "Falha ao consultar Gemini API para help chat: %s", exc
            )

    groq_key = getattr(settings, "GROQ_API_KEY", None)
    if groq_key:
        try:
            model = getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {groq_key}"}
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {
                        "role": "user",
                        "content": (
                            f"Contexto:\n{context_text}\n\n"
                            f"Pergunta: {question}"
                        ),
                    },
                ],
                "temperature": 0.2,
                "max_tokens": 800,
            }
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get(
                            "content", ""
                        ).strip()
                        if content:
                            return content
                logger.warning(
                    "Groq API returned status %s: %s",
                    resp.status_code,
                    resp.text[:200],
                )
        except Exception as exc:
            logger.warning(
                "Falha ao consultar Groq API para help chat: %s", exc
            )

    return None


class HelpDocumentChatService:
    """Read-only lexical retrieval over an explicit allowlist of user docs."""

    def __init__(self, document_root: Path):
        self._chunks = self._load_chunks(document_root)

    @staticmethod
    def _load_chunks(document_root: Path) -> tuple[_DocumentChunk, ...]:
        chunks: list[_DocumentChunk] = []
        for filename, display_name in _ALLOWED_DOCUMENTS:
            path = document_root / filename
            if not path.is_file():
                continue
            content = path.read_text(encoding="utf-8")
            headings = list(_HEADING_PATTERN.finditer(content))
            if not headings:
                section_texts = [(display_name, display_name, content)]
            else:
                section_texts: list[tuple[str, str, str]] = []
                first_heading = headings[0]
                if content[:first_heading.start()].strip():
                    section_texts.append(
                        (
                            display_name,
                            display_name,
                            content[:first_heading.start()],
                        )
                    )
                heading_path: list[str] = []
                for index, heading in enumerate(headings):
                    end = (
                        headings[index + 1].start()
                        if index + 1 < len(headings)
                        else len(content)
                    )
                    level = len(heading.group(1))
                    title = heading.group(2).strip()
                    heading_path = heading_path[: level - 1]
                    heading_path.append(title)
                    section_texts.append(
                        (
                            title,
                            " ".join(heading_path),
                            content[heading.end():end],
                        )
                    )

            for section, heading_context, section_text in section_texts:
                if not _is_searchable_section(filename, section):
                    continue
                for text in _split_paragraphs(_clean_markdown(section_text)):
                    tokens = _tokens(f"{heading_context} {section} {text}")
                    if tokens:
                        chunks.append(
                            _DocumentChunk(
                                display_name, section, text, tokens
                            )
                        )
        return tuple(chunks)

    def _retrieve_sources(
        self, question: str, limit: int = 3
    ) -> tuple[list[HelpChatSource], set[str]]:
        query_tokens = _tokens(question)
        if not query_tokens or not self._chunks:
            return [], set()

        query = set(query_tokens)
        document_frequency: Counter[str] = Counter()
        chunk_counters = [Counter(chunk.tokens) for chunk in self._chunks]
        for counts in chunk_counters:
            document_frequency.update(counts.keys())

        scored: list[tuple[float, _DocumentChunk]] = []
        for chunk, counts in zip(self._chunks, chunk_counters, strict=True):
            matched = query.intersection(counts)
            coverage = len(matched) / len(query)
            if coverage < 0.34:
                continue
            score = sum(
                (
                    1
                    + math.log(
                        (len(self._chunks) + 1)
                        / (document_frequency[token] + 1)
                    )
                )
                * (1 + math.log(counts[token]))
                for token in matched
            )
            heading_terms = query.intersection(_tokens(chunk.section))
            score += 1.5 * len(heading_terms)
            scored.append((score * coverage, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)
        selected: list[_DocumentChunk] = []
        seen_sections: set[tuple[str, str]] = set()
        for _, chunk in scored:
            key = (chunk.document, chunk.section)
            if key in seen_sections:
                continue
            selected.append(chunk)
            seen_sections.add(key)
            if len(selected) == limit:
                break

        if not selected:
            return [], query

        sources = [
            HelpChatSource(
                document=chunk.document,
                section=chunk.section,
                excerpt=_relevant_excerpt(chunk.text, query),
            )
            for chunk in selected
        ]
        return sources, query

    def answer(self, question: str, limit: int = 3) -> HelpChatResponse:
        sources, _ = self._retrieve_sources(question, limit=limit)
        if not sources:
            return HelpChatResponse(
                answer=_NO_MATCH_ANSWER,
                sources=[],
                suggested_routes=[],
                mode="deterministic",
            )

        routes = _suggest_routes(question, sources)
        answer = (
            "Encontrei estes trechos na documentação do sistema. "
            "Eles são apresentados como fonte para você conferir o "
            "contexto completo."
        )
        return HelpChatResponse(
            answer=answer,
            sources=sources,
            suggested_routes=routes,
            mode="deterministic",
        )

    async def answer_async(
        self, question: str, limit: int = 3
    ) -> HelpChatResponse:
        sources, _ = self._retrieve_sources(question, limit=limit)
        if not sources:
            return HelpChatResponse(
                answer=_NO_MATCH_ANSWER,
                sources=[],
                suggested_routes=[],
                mode="deterministic",
            )

        routes = _suggest_routes(question, sources)

        llm_answer = await _synthesize_answer_with_llm(question, sources)
        if llm_answer:
            return HelpChatResponse(
                answer=llm_answer,
                sources=sources,
                suggested_routes=routes,
                mode="llm",
            )

        answer = (
            "Encontrei estes trechos na documentação do sistema. "
            "Eles são apresentados como fonte para você conferir o "
            "contexto completo."
        )
        return HelpChatResponse(
            answer=answer,
            sources=sources,
            suggested_routes=routes,
            mode="deterministic",
        )


def _default_document_root() -> Path:
    runtime_root = Path(__file__).resolve().parents[2] / "help_docs"
    if runtime_root.is_dir():
        return runtime_root
    repository_root = Path(__file__).resolve().parents[3]
    return repository_root / "docs"


@lru_cache(maxsize=1)
def get_help_document_chat_service() -> HelpDocumentChatService:
    return HelpDocumentChatService(_default_document_root())
