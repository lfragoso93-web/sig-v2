"""Servico de envio de e-mails transacionais (Brevo / SMTP).

Utiliza smtplib em thread separada com asyncio.to_thread para nao bloquear
o event loop do FastAPI/Starlette.
"""

import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import smtplib
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def _send_smtp_sync(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
) -> bool:
    """Envio sincrono via smtplib."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.info(
            "SMTP_USER/PASSWORD nao configurados. Simulando envio para %s: %s",
            to_email,
            subject,
        )
        return True

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    from_header = (
        f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
    )
    msg["From"] = from_header
    msg["To"] = to_email

    plain_part = MIMEText(
        text_body or html_body, "plain", _charset="utf-8"
    )
    html_part = MIMEText(html_body, "html", _charset="utf-8")
    msg.attach(plain_part)
    msg.attach(html_part)

    try:
        with smtplib.SMTP(
            settings.SMTP_HOST, settings.SMTP_PORT, timeout=15
        ) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        logger.info("E-mail enviado com sucesso para %s", to_email)
        return True
    except Exception as exc:
        logger.error(
            "Falha ao enviar e-mail para %s via SMTP (%s): %s",
            to_email,
            settings.SMTP_HOST,
            exc,
        )
        return False


async def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
) -> bool:
    """Dispara o envio de e-mail assincrono via threadpool."""
    return await asyncio.to_thread(
        _send_smtp_sync, to_email, subject, html_body, text_body
    )


async def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """Envia e-mail com link para redefinicao de senha."""
    reset_url = (
        f"{settings.FRONTEND_URL}/auth/redefinir-senha?token={reset_token}"
    )
    subject = "SGI v2 — Recuperação de Senha"
    html_body = (
        "<!DOCTYPE html><html>"
        "<body style=\"font-family: sans-serif; color: #1a1a1a; "
        "padding: 20px;\">"
        "<div style=\"max-width: 560px; margin: 0 auto; "
        "border: 1px solid #e5e7eb; border-radius: 8px; padding: 32px;\">"
        "<h2 style=\"color: #0d9488;\">SGI v2</h2>"
        "<h3>Recuperação de Senha</h3>"
        "<p>Olá,</p>"
        "<p>Recebemos uma solicitação para redefinir sua senha.</p>"
        "<p>Clique no botão abaixo (válido por 30 minutos):</p>"
        "<div style=\"margin: 28px 0; text-align: center;\">"
        f"<a href=\"{reset_url}\" style=\"background: #0d9488; color: #fff; "
        "padding: 12px 24px; text-decoration: none; border-radius: 6px; "
        "font-weight: 600; display: inline-block;\">Redefinir Senha</a>"
        "</div>"
        "<p style=\"font-size: 12px; color: #6b7280;\">"
        f"Ou acesse: {reset_url}</p>"
        "<hr style=\"border-top: 1px solid #e5e7eb; margin: 24px 0;\" />"
        "<p style=\"font-size: 12px; color: #9ca3af;\">"
        "Se não solicitou a alteração, ignore este e-mail.</p>"
        "</div></body></html>"
    )
    text_body = (
        "Recuperação de Senha — SGI v2\n\n"
        "Olá,\n"
        "Acesse o link abaixo para redefinir sua senha (válido por 30 min):\n"
        f"{reset_url}\n\n"
        "Se não solicitou este e-mail, ignore-o.\n"
    )
    return await send_email(to_email, subject, html_body, text_body)


async def send_welcome_email(to_email: str, name: str) -> bool:
    """Envia e-mail de boas-vindas apos cadastro."""
    subject = "Bem-vindo ao SGI v2!"
    dashboard_url = f"{settings.FRONTEND_URL}/carteira"
    html_body = (
        "<!DOCTYPE html><html>"
        "<body style=\"font-family: sans-serif; color: #1a1a1a; "
        "padding: 20px;\">"
        "<div style=\"max-width: 560px; margin: 0 auto; "
        "border: 1px solid #e5e7eb; border-radius: 8px; padding: 32px;\">"
        "<h2 style=\"color: #0d9488;\">SGI v2</h2>"
        f"<h3>Bem-vindo(a), {name}!</h3>"
        "<p>Sua conta no SGI v2 foi criada com sucesso.</p>"
        "<div style=\"margin: 28px 0; text-align: center;\">"
        f"<a href=\"{dashboard_url}\" style=\"background: #0d9488; color: "
        "#fff; padding: 12px 24px; text-decoration: none; border-radius: "
        "6px; font-weight: 600; display: inline-block;\">Acessar o SGI</a>"
        "</div>"
        "<hr style=\"border-top: 1px solid #e5e7eb; margin: 24px 0;\" />"
        "<p style=\"font-size: 12px; color: #9ca3af;\">"
        "SGI v2 — Gestão Inteligente de Investimentos.</p>"
        "</div></body></html>"
    )
    text_body = (
        f"Bem-vindo(a) ao SGI v2, {name}!\n\n"
        "Sua conta foi criada com sucesso.\n"
        f"Acesse em: {dashboard_url}\n"
    )
    return await send_email(to_email, subject, html_body, text_body)
