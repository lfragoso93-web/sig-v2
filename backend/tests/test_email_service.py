"""Testes para email_service (Brevo / SMTP)."""

import pytest
from app.services.email_service import (
    send_email,
    send_password_reset_email,
    send_welcome_email,
)


@pytest.mark.asyncio
async def test_send_email_mock_when_smtp_not_configured():
    # Sem credenciais SMTP definidas, simula envio com sucesso
    res = await send_email(
        to_email="teste@sgi.com",
        subject="Assunto Teste",
        html_body="<p>Conteudo</p>",
    )
    assert res is True


@pytest.mark.asyncio
async def test_send_password_reset_email():
    res = await send_password_reset_email(
        to_email="investidor@sgi.com",
        reset_token="sample-reset-token-xyz",
    )
    assert res is True


@pytest.mark.asyncio
async def test_send_welcome_email():
    res = await send_welcome_email(
        to_email="novo@sgi.com",
        name="Investidor Alfa",
    )
    assert res is True
