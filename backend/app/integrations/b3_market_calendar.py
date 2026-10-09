"""Narrow HTTP boundary for the official annual B3 calendar publication."""

from __future__ import annotations

from urllib.parse import urlsplit

import httpx


_B3_HOST = "www.b3.com.br"
_MAX_RESPONSE_BYTES = 2_000_000
_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


def _validate_b3_source_url(source_url: str) -> None:
    parsed = urlsplit(source_url)
    if parsed.scheme != "https" or parsed.hostname != _B3_HOST:
        raise ValueError("B3 calendar source URL must use official HTTPS host")


async def fetch_b3_annual_calendar_page(
    source_url: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> str:
    """Fetch a bounded page from B3 without following a redirect elsewhere."""
    _validate_b3_source_url(source_url)
    owns_client = client is None
    active_client = client or httpx.AsyncClient(
        timeout=_TIMEOUT,
        follow_redirects=False,
    )
    try:
        response = await active_client.get(source_url)
        response.raise_for_status()
        if len(response.content) > _MAX_RESPONSE_BYTES:
            raise ValueError(
                "B3 calendar source response exceeds maximum size"
            )
        return response.text
    finally:
        if owns_client:
            await active_client.aclose()
