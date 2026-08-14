"""Helpers para manter valores externos em uma unica linha de log."""

from __future__ import annotations

_MAX_LOG_VALUE_LENGTH = 500


def sanitize_log_value(value: object, *, max_length: int = _MAX_LOG_VALUE_LENGTH) -> str:
    """Escapa separadores de linha e limita valores antes de envia-los ao logger."""

    text = str(value)
    sanitized = (
        text.replace("\r", "\\r")
        .replace("\n", "\\n")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    return sanitized[:max_length]
