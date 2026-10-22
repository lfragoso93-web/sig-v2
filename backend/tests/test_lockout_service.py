"""Testes para lockout_service (protecao contra forca bruta)."""

import pytest
from fastapi import HTTPException
from app.services.lockout_service import (
    check_lockout,
    clear_lockout,
    register_failed_attempt,
)


@pytest.mark.asyncio
async def test_lockout_after_max_attempts():
    test_email = "bruteforce_test@sgi.com"
    await clear_lockout(test_email)

    # 4 falhas nao bloqueiam
    for _ in range(4):
        await register_failed_attempt(test_email)
    await check_lockout(test_email)  # Nao deve levantar excecao

    # 5ª falha ativa o lockout
    await register_failed_attempt(test_email)

    with pytest.raises(HTTPException) as exc_info:
        await check_lockout(test_email)
    assert exc_info.value.status_code == 429

    # Limpa lockout
    await clear_lockout(test_email)
    await check_lockout(test_email)  # Nao deve levantar excecao
