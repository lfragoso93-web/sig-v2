"""Servico de envio de e-mails transacionais (Brevo / SMTP).

Utiliza smtplib em thread separada com asyncio.to_thread para nao bloquear
o event loop do FastAPI/Starlette.
"""

import asyncio
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import smtplib
from time import monotonic
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def _mask_smtp_user(user: Optional[str]) -> Optional[str]:
    if not user or not user.strip():
        return None
    raw = user.strip()
    if "@" in raw:
        local, domain = raw.split("@", 1)
        prefix = local[:2] if len(local) > 2 else local[:1]
        return f"{prefix}***@{domain}"
    prefix = raw[:2] if len(raw) > 2 else raw[:1]
    return f"{prefix}***"


def get_smtp_status() -> dict:
    """Retorna o diagnostico de configuracao SMTP sem expor segredos."""
    configured = bool(
        settings.SMTP_USER
        and settings.SMTP_USER.strip()
        and settings.SMTP_PASSWORD
        and settings.SMTP_PASSWORD.strip()
    )
    return {
        "configured": configured,
        "mode": "live" if configured else "simulation",
        "host": settings.SMTP_HOST,
        "port": settings.SMTP_PORT,
        "use_tls": settings.SMTP_USE_TLS,
        "smtp_user_masked": _mask_smtp_user(settings.SMTP_USER),
        "from_email": settings.EMAILS_FROM_EMAIL,
        "from_name": settings.EMAILS_FROM_NAME,
    }


def _send_smtp_test_sync(to_email: str) -> dict:
    """Executa teste real de conexao, autenticacao e envio via SMTP."""
    started = monotonic()
    status_info = get_smtp_status()
    if not status_info["configured"]:
        return {
            "ok": False,
            "simulated": True,
            "to_email": to_email,
            "host": settings.SMTP_HOST,
            "port": settings.SMTP_PORT,
            "duration_ms": 0,
            "message": (
                "SMTP_USER e/ou SMTP_PASSWORD estão vazios no .env "
                "(modo simulação ativo — nenhum e-mail real foi enviado). "
                "Preencha as credenciais no .env e recrie o container backend."
            ),
            "error": "Credenciais SMTP não configuradas",
        }

    now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")
    subject = "SGI v2 — Teste de Configuração SMTP"
    html_body = (
        "<!DOCTYPE html><html>"
        "<body style=\"font-family: sans-serif; color: #1a1a1a; padding: 20px;\">"
        "<div style=\"max-width: 560px; margin: 0 auto; "
        "border: 1px solid #e5e7eb; border-radius: 8px; padding: 32px;\">"
        "<h2 style=\"color: #0d9488; margin-top: 0;\">SGI v2 — Diagnóstico SMTP</h2>"
        "<p>Este é um e-mail de teste disparado pelo <strong>Painel Administrativo</strong> do SGI v2.</p>"
        "<ul style=\"font-size: 13px; color: #374151; line-height: 1.6;\">"
        f"<li><strong>Servidor:</strong> {settings.SMTP_HOST}:{settings.SMTP_PORT} (TLS: {'Sim' if settings.SMTP_USE_TLS else 'Não'})</li>"
        f"<li><strong>Remetente:</strong> {settings.EMAILS_FROM_NAME} &lt;{settings.EMAILS_FROM_EMAIL}&gt;</li>"
        f"<li><strong>Horário:</strong> {now_str}</li>"
        "</ul>"
        "<p style=\"font-size: 12px; color: #059669; font-weight: 600;\">"
        "Se você recebeu esta mensagem, o envio de e-mails transacionais está funcionando perfeitamente."
        "</p>"
        "</div></body></html>"
    )
    text_body = (
        "SGI v2 — Diagnóstico SMTP\n\n"
        "Este é um e-mail de teste disparado pelo Painel Administrativo do SGI v2.\n"
        f"Servidor: {settings.SMTP_HOST}:{settings.SMTP_PORT}\n"
        f"Remetente: {settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>\n"
        f"Horário: {now_str}\n"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain", _charset="utf-8"))
    msg.attach(MIMEText(html_body, "html", _charset="utf-8"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            server.ehlo()
            if settings.SMTP_USE_TLS:
                server.starttls()
                server.ehlo()
            server.login(settings.SMTP_USER or "", settings.SMTP_PASSWORD or "")
            server.send_message(msg)
        duration_ms = int(round((monotonic() - started) * 1000))
        logger.info("[SMTP Test] E-mail de teste enviado com sucesso para %s (%d ms)", to_email, duration_ms)
        return {
            "ok": True,
            "simulated": False,
            "to_email": to_email,
            "host": settings.SMTP_HOST,
            "port": settings.SMTP_PORT,
            "duration_ms": duration_ms,
            "message": f"E-mail de teste enviado com sucesso para {to_email} ({duration_ms} ms).",
            "error": None,
        }
    except Exception as exc:
        duration_ms = int(round((monotonic() - started) * 1000))
        logger.error(
            "[SMTP Test] Falha ao enviar e-mail de teste para %s via %s:%s: %s",
            to_email,
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            exc,
        )
        return {
            "ok": False,
            "simulated": False,
            "to_email": to_email,
            "host": settings.SMTP_HOST,
            "port": settings.SMTP_PORT,
            "duration_ms": duration_ms,
            "message": f"Falha na conexão ou autenticação com {settings.SMTP_HOST}:{settings.SMTP_PORT}.",
            "error": str(exc),
        }


async def send_smtp_test_email(to_email: str) -> dict:
    """Dispara o teste de SMTP em thread separada e retorna diagnostico detalhado."""
    return await asyncio.to_thread(_send_smtp_test_sync, to_email)


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


async def send_password_changed_email(
    to_email: str,
    name: str,
    origin: str = "redefinição de senha",
) -> bool:
    """Envia aviso de seguranca quando a senha da conta e alterada."""
    now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y às %H:%M UTC")
    login_url = f"{settings.FRONTEND_URL}/auth/login"
    subject = "SGI v2 — Aviso de Segurança: Senha Alterada"
    html_body = (
        "<!DOCTYPE html><html>"
        "<body style=\"font-family: sans-serif; color: #1a1a1a; padding: 20px;\">"
        "<div style=\"max-width: 560px; margin: 0 auto; "
        "border: 1px solid #e5e7eb; border-radius: 8px; padding: 32px;\">"
        "<h2 style=\"color: #0d9488; margin-top: 0;\">SGI v2</h2>"
        "<h3>Sua senha foi alterada</h3>"
        f"<p>Olá, <strong>{name}</strong>,</p>"
        f"<p>Informamos que a senha da sua conta foi alterada ({origin}) em <strong>{now_str}</strong>.</p>"
        "<p style=\"font-size: 13px; color: #4b5563;\">"
        "Se foi você quem realizou esta alteração, nenhuma ação adicional é necessária."
        "</p>"
        "<div style=\"margin: 24px 0; text-align: center;\">"
        f"<a href=\"{login_url}\" style=\"background: #0d9488; color: #fff; "
        "padding: 12px 24px; text-decoration: none; border-radius: 6px; "
        "font-weight: 600; display: inline-block;\">Acessar Minha Conta</a>"
        "</div>"
        "<hr style=\"border-top: 1px solid #e5e7eb; margin: 24px 0;\" />"
        "<p style=\"font-size: 12px; color: #dc2626;\">"
        "Caso não reconheça esta atividade, utilize imediatamente a opção 'Esqueci minha senha' na tela de login."
        "</p>"
        "</div></body></html>"
    )
    text_body = (
        f"Olá, {name},\n\n"
        f"A senha da sua conta no SGI v2 foi alterada ({origin}) em {now_str}.\n"
        "Se não reconhece esta atividade, redefina sua senha imediatamente.\n"
        f"Acesso: {login_url}\n"
    )
    return await send_email(to_email, subject, html_body, text_body)


async def send_account_status_email(
    to_email: str,
    name: str,
    is_active: bool,
) -> bool:
    """Envia aviso quando a conta do usuario e ativada ou desativada."""
    status_label = "Ativada" if is_active else "Desativada"
    dashboard_url = f"{settings.FRONTEND_URL}/carteira"
    subject = f"SGI v2 — Sua conta foi {status_label.lower()}"
    action_block = (
        "<div style=\"margin: 24px 0; text-align: center;\">"
        f"<a href=\"{dashboard_url}\" style=\"background: #0d9488; color: #fff; "
        "padding: 12px 24px; text-decoration: none; border-radius: 6px; "
        "font-weight: 600; display: inline-block;\">Acessar o SGI</a>"
        "</div>"
        if is_active
        else "<p style=\"font-size: 13px; color: #6b7280;\">Em caso de dúvidas, entre em contato com o administrador do sistema.</p>"
    )
    html_body = (
        "<!DOCTYPE html><html>"
        "<body style=\"font-family: sans-serif; color: #1a1a1a; padding: 20px;\">"
        "<div style=\"max-width: 560px; margin: 0 auto; "
        "border: 1px solid #e5e7eb; border-radius: 8px; padding: 32px;\">"
        "<h2 style=\"color: #0d9488; margin-top: 0;\">SGI v2</h2>"
        f"<h3>Conta {status_label}</h3>"
        f"<p>Olá, <strong>{name}</strong>,</p>"
        f"<p>O status da sua conta no SGI v2 foi atualizado para: <strong>{status_label}</strong>.</p>"
        f"{action_block}"
        "<hr style=\"border-top: 1px solid #e5e7eb; margin: 24px 0;\" />"
        "<p style=\"font-size: 12px; color: #9ca3af;\">"
        "SGI v2 — Gestão Inteligente de Investimentos.</p>"
        "</div></body></html>"
    )
    text_body = (
        f"Olá, {name},\n\n"
        f"O status da sua conta no SGI v2 foi atualizado para: {status_label}.\n"
    )
    return await send_email(to_email, subject, html_body, text_body)


async def send_account_deleted_email(to_email: str, name: str) -> bool:
    """Envia confirmacao de encerramento de conta e exclusao dos dados."""
    now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y às %H:%M UTC")
    subject = "SGI v2 — Confirmação de Exclusão de Conta"
    html_body = (
        "<!DOCTYPE html><html>"
        "<body style=\"font-family: sans-serif; color: #1a1a1a; padding: 20px;\">"
        "<div style=\"max-width: 560px; margin: 0 auto; "
        "border: 1px solid #e5e7eb; border-radius: 8px; padding: 32px;\">"
        "<h2 style=\"color: #0d9488; margin-top: 0;\">SGI v2</h2>"
        "<h3>Conta Excluída</h3>"
        f"<p>Olá, <strong>{name}</strong>,</p>"
        f"<p>Confirmamos que sua conta no SGI v2 e todas as carteiras e registros vinculados foram permanentemente excluídos em <strong>{now_str}</strong>.</p>"
        "<hr style=\"border-top: 1px solid #e5e7eb; margin: 24px 0;\" />"
        "<p style=\"font-size: 12px; color: #9ca3af;\">"
        "Agradecemos por ter utilizado o SGI v2.</p>"
        "</div></body></html>"
    )
    text_body = (
        f"Olá, {name},\n\n"
        f"Confirmamos que sua conta no SGI v2 e todos os dados vinculados foram permanentemente excluídos em {now_str}.\n"
    )
    return await send_email(to_email, subject, html_body, text_body)


def _format_brl(value: float) -> str:
    formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


async def send_dividend_payment_summary_email(
    to_email: str,
    name: str,
    payment_date_str: str,
    items: list[dict],
    total_net_brl: float,
) -> bool:
    """Envia resumo matinal de proventos com pagamento agendado para o dia."""
    proventos_url = f"{settings.FRONTEND_URL}/carteira/proventos"
    subject = f"SGI v2 — Proventos Creditados Hoje ({payment_date_str})"

    rows_html = "".join(
        "<tr style=\"border-bottom: 1px solid #f3f4f6;\">"
        f"<td style=\"padding: 8px 6px; font-weight: 600;\">{item['ticker']}</td>"
        f"<td style=\"padding: 8px 6px; color: #4b5563;\">{item['event_type']}</td>"
        f"<td style=\"padding: 8px 6px; color: #4b5563;\">{item['portfolio_name']}</td>"
        f"<td style=\"padding: 8px 6px; text-align: right; font-weight: 600; color: #059669;\">{_format_brl(float(item['net_amount']))}</td>"
        "</tr>"
        for item in items
    )

    html_body = (
        "<!DOCTYPE html><html>"
        "<body style=\"font-family: sans-serif; color: #1a1a1a; padding: 20px;\">"
        "<div style=\"max-width: 580px; margin: 0 auto; "
        "border: 1px solid #e5e7eb; border-radius: 8px; padding: 32px;\">"
        "<h2 style=\"color: #0d9488; margin-top: 0;\">SGI v2 — Aviso de Proventos</h2>"
        f"<p>Olá, <strong>{name}</strong>,</p>"
        f"<p>Você possui proventos com pagamento programado para hoje (<strong>{payment_date_str}</strong>):</p>"
        "<table style=\"width: 100%; border-collapse: collapse; font-size: 13px; margin: 16px 0;\">"
        "<thead>"
        "<tr style=\"border-bottom: 2px solid #e5e7eb; text-align: left; color: #6b7280;\">"
        "<th style=\"padding: 8px 6px;\">Ativo</th>"
        "<th style=\"padding: 8px 6px;\">Tipo</th>"
        "<th style=\"padding: 8px 6px;\">Carteira</th>"
        "<th style=\"padding: 8px 6px; text-align: right;\">Valor Líquido</th>"
        "</tr>"
        "</thead>"
        f"<tbody>{rows_html}</tbody>"
        "<tfoot>"
        "<tr style=\"border-top: 2px solid #e5e7eb; font-weight: 700;\">"
        "<td colspan=\"3\" style=\"padding: 10px 6px;\">Total Líquido do Dia</td>"
        f"<td style=\"padding: 10px 6px; text-align: right; color: #059669;\">{_format_brl(total_net_brl)}</td>"
        "</tr>"
        "</tfoot>"
        "</table>"
        "<div style=\"margin: 24px 0; text-align: center;\">"
        f"<a href=\"{proventos_url}\" style=\"background: #0d9488; color: #fff; "
        "padding: 12px 24px; text-decoration: none; border-radius: 6px; "
        "font-weight: 600; display: inline-block;\">Ver Detalhes em Proventos</a>"
        "</div>"
        "<hr style=\"border-top: 1px solid #e5e7eb; margin: 24px 0;\" />"
        "<p style=\"font-size: 12px; color: #9ca3af;\">"
        "SGI v2 — Gestão Inteligente de Investimentos.</p>"
        "</div></body></html>"
    )

    text_lines = [
        f"Olá, {name},",
        "",
        f"Você possui proventos com pagamento programado para hoje ({payment_date_str}):",
        "",
    ]
    for item in items:
        text_lines.append(
            f"- {item['ticker']} ({item['event_type']}) [{item['portfolio_name']}]: {_format_brl(float(item['net_amount']))}"
        )
    text_lines.extend([
        "",
        f"Total Líquido do Dia: {_format_brl(total_net_brl)}",
        f"Ver detalhes: {proventos_url}",
    ])
    return await send_email(to_email, subject, html_body, "\n".join(text_lines))

