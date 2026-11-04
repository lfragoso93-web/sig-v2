from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.schemas.help_chat import HelpChatResponse, HelpChatSource

_ALLOWED_DOCUMENTS = (
    ("DOCUMENTACAO_DO_SISTEMA.md", "Manual do sistema"),
    ("rentabilidade.md", "Rentabilidade"),
    ("TOOLS_CALCULATORS.md", "Calculadoras e simuladores"),
    ("snapshots.md", "Snapshots e TWR"),
    ("GOALS_AND_ANALYSIS_CONTRACT.md", "Metas e análise de carteira"),
    ("CORPORATE_ACTIONS.md", "Eventos corporativos"),
)
_WORD_PATTERN = re.compile(r"[a-z0-9]{3,}")
_HEADING_PATTERN = re.compile(r"^#{1,4}\s+(.+?)\s*#*\s*$", re.MULTILINE)
_STOP_WORDS = frozenset(
    "a o as os um uma uns umas de da do das dos em no na nos nas por para com sem que como qual quais quando onde porque e ou se ao aos pelo pela pelos pelas sua seu suas seus isso esta este esse essa isto mais menos muito muita sobre entre desde ate ser ter pode podem sistema carteira dados voce usuario usar do da faz fazer sao foi".split()
)
_NO_MATCH_ANSWER = (
    "Não encontrei uma resposta suficiente nos documentos disponíveis. "
    "Tente reformular a pergunta ou consulte as perguntas frequentes desta página."
)


@dataclass(frozen=True)
class _DocumentChunk:
    document: str
    section: str
    text: str
    tokens: tuple[str, ...]


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _tokens(value: str) -> tuple[str, ...]:
    return tuple(
        token for token in _WORD_PATTERN.findall(_normalize(value))
        if token not in _STOP_WORDS
    )


def _clean_markdown(value: str) -> str:
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    cleaned = re.sub(r"```[^\n]*\n?(.*?)```", r"\1", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"[`*_~]", "", cleaned)
    cleaned = re.sub(r"^\s*[-|>]+\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\|", " · ", cleaned)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def _split_paragraphs(text: str, max_chars: int = 1500) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(
                paragraph[index:index + max_chars]
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
                section_texts = [(display_name, content)]
            else:
                section_texts: list[tuple[str, str]] = []
                first_heading = headings[0]
                if content[:first_heading.start()].strip():
                    section_texts.append((display_name, content[:first_heading.start()]))
                for index, heading in enumerate(headings):
                    end = headings[index + 1].start() if index + 1 < len(headings) else len(content)
                    section_texts.append((heading.group(1).strip(), content[heading.end():end]))

            for section, section_text in section_texts:
                # Historical action lists and roadmaps are not current user guidance.
                if _normalize(section).startswith(("pendencias", "roadmap", "historico", "diagnostico historico")):
                    continue
                for text in _split_paragraphs(_clean_markdown(section_text)):
                    tokens = _tokens(f"{section} {text}")
                    if tokens:
                        chunks.append(_DocumentChunk(display_name, section, text, tokens))
        return tuple(chunks)

    def answer(self, question: str, limit: int = 3) -> HelpChatResponse:
        query_tokens = _tokens(question)
        if not query_tokens or not self._chunks:
            return HelpChatResponse(answer=_NO_MATCH_ANSWER)

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
                (1 + math.log((len(self._chunks) + 1) / (document_frequency[token] + 1)))
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
            return HelpChatResponse(answer=_NO_MATCH_ANSWER)

        sources = [
            HelpChatSource(
                document=chunk.document,
                section=chunk.section,
                excerpt=chunk.text[:700].strip(),
            )
            for chunk in selected
        ]
        answer = (
            "Encontrei estes trechos na documentação do sistema. "
            "Eles são apresentados como fonte para você conferir o contexto completo."
        )
        return HelpChatResponse(answer=answer, sources=sources)


def _default_document_root() -> Path:
    runtime_root = Path(__file__).resolve().parents[2] / "help_docs"
    if runtime_root.is_dir():
        return runtime_root
    repository_root = Path(__file__).resolve().parents[3]
    return repository_root / "docs"


@lru_cache(maxsize=1)
def get_help_document_chat_service() -> HelpDocumentChatService:
    return HelpDocumentChatService(_default_document_root())
