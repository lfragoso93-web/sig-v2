"""Auditoria estrutural dos CSVs do Tesouro Transparente.

Não registra preços nem expõe valores financeiros. Lista somente cabeçalhos e
combinações distintas de tipo de título/vencimento relevantes para normalização.
"""
from __future__ import annotations

import csv
import io
import re
import unicodedata

import httpx

from app.integrations.tesouro_transparente import discover_csv_resources


def _normalize(value: str | None) -> str:
    raw = unicodedata.normalize("NFKD", value or "")
    raw = "".join(ch for ch in raw if not unicodedata.combining(ch))
    raw = raw.lower().replace("+", " mais ")
    raw = re.sub(r"[^a-z0-9]+", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()


def _first(row: dict[str, str], *names: str) -> str:
    normalized = {str(key).strip().lower(): value for key, value in row.items()}
    for name in names:
        value = normalized.get(name.lower())
        if value not in (None, ""):
            return str(value).strip()
    return ""


def inspect_csv_structure(text: str) -> dict[str, object]:
    sample = text[:8192]
    delimiter = ";" if sample.count(";") >= sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)

    headers = [str(value).strip() for value in (reader.fieldnames or [])]
    relevant: set[tuple[str, str]] = set()
    title_samples: set[tuple[str, str]] = set()
    rows = 0

    for row in reader:
        rows += 1
        title = _first(row, "Tipo Titulo", "Tipo Título", "Titulo", "Título", "Nome")
        maturity = _first(row, "Data Vencimento", "Vencimento")
        normalized = _normalize(title)
        if title and len(title_samples) < 100:
            title_samples.add((title, maturity))
        if any(token in normalized for token in ("renda", "aposentadoria", "educa")):
            relevant.add((title, maturity))

    return {
        "headers": headers,
        "rows": rows,
        "relevant_titles": [
            {"title": title, "maturity": maturity}
            for title, maturity in sorted(relevant)
        ],
        "title_samples": [
            {"title": title, "maturity": maturity}
            for title, maturity in sorted(title_samples)[:50]
        ],
    }


async def audit_tesouro_transparente_resources() -> dict[str, object]:
    resources_result: list[dict[str, object]] = []
    async with httpx.AsyncClient(timeout=90.0, follow_redirects=True) as client:
        urls = await discover_csv_resources(client)
        for url in urls:
            try:
                response = await client.get(url, timeout=120.0)
                response.raise_for_status()
                detail = inspect_csv_structure(response.text)
                detail["url"] = url
                detail["ok"] = True
            except Exception as exc:
                detail = {"url": url, "ok": False, "error": str(exc)}
            resources_result.append(detail)

    relevant_total = sum(
        len(item.get("relevant_titles") or [])
        for item in resources_result
        if item.get("ok")
    )
    return {
        "resources": len(resources_result),
        "relevant_titles": relevant_total,
        "items": resources_result,
        "destructive_changes": False,
    }
