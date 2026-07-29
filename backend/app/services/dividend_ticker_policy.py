"""Política compartilhada de elegibilidade de tickers para eventos globais."""

from __future__ import annotations

import re

_MAIN_EQUITY_RE = re.compile(r"^[A-Z0-9]{4,6}(3|4|5|6|11|31|32|33|34|35)$")


def is_event_ticker(ticker: str) -> bool:
    """Aceita o ativo principal e rejeita frações, direitos e recibos."""

    normalized = ticker.strip().upper()
    if normalized.endswith("F"):
        return False
    if normalized[-1:] in {"B", "D", "R"}:
        return False
    if normalized[-2:] in {"97", "98", "99"}:
        return False
    return bool(_MAIN_EQUITY_RE.match(normalized))
