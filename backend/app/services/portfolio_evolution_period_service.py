"""Fronteiras temporais canônicas para leitura da evolução patrimonial."""
from __future__ import annotations

from datetime import date


def monthly_window_start(months: int, *, today: date | None = None) -> date | None:
    """Retorna o primeiro dia da janela com exatamente ``months`` meses-calendário.

    O mês corrente conta como o último mês da janela. Zero representa todo o
    histórico e, portanto, não possui fronteira inicial.
    """
    if months <= 0:
        return None

    current_month = (today or date.today()).replace(day=1)
    month_index = current_month.year * 12 + current_month.month - 1 - (months - 1)
    return date(month_index // 12, month_index % 12 + 1, 1)
