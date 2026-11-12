"""Envío del enlace de acceso por correo (sin dependencias externas).

Proveedores soportados, elegidos con ``EMAIL_PROVIDER`` o por detección:

- ``resend``  → API HTTP de <https://resend.com> (``RESEND_API_KEY``).
- ``smtp``    → cualquier SMTP con usuario/contraseña (Brevo, Gmail, Mailgun…).
- ``console`` → sin configurar: el enlace se imprime en el log del servidor.
                Es el modo de desarrollo; en producción hace falta un proveedor.

Variables:

    EMAIL_PROVIDER   resend | smtp | console (opcional, autodetectado)
    EMAIL_FROM       remitente, p. ej. "ApuestaEdge <acceso@tudominio.com>"
    RESEND_API_KEY   si se usa Resend
    SMTP_HOST        p. ej. smtp-relay.brevo.com
    SMTP_PORT        587 (STARTTLS) o 465 (SSL)
    SMTP_USER / SMTP_PASSWORD
    SMTP_SSL         1 para forzar SSL (se infiere del puerto 465)
"""

from __future__ import annotations

import asyncio
import os
import smtplib
import ssl
from email.message import EmailMessage

import httpx

RESEND_API = "https://api.resend.com/emails"


def provider() -> str:
    """Proveedor activo: ``resend``, ``smtp`` o ``console``."""
    explicit = os.environ.get("EMAIL_PROVIDER", "").strip().lower()
    if explicit in {"resend", "smtp", "console"}:
        return explicit
    if os.environ.get("RESEND_API_KEY", "").strip():
        return "resend"
    if os.environ.get("SMTP_HOST", "").strip():
        return "smtp"
    return "console"


def configured() -> bool:
    """True si se puede entregar correo de verdad (no solo al log)."""
    return provider() != "console"


def sender() -> str:
    return (os.environ.get("EMAIL_FROM", "").strip()
            or "ApuestaEdge <no-reply@apuestaedge.app>")


def _subject() -> str:
    return "Tu enlace de acceso a ApuestaEdge"


def _text(url: str, ttl_minutes: int) -> str:
    return (
        "Entra en ApuestaEdge con este enlace:\n\n"
        f"{url}\n\n"
        f"Caduca en {ttl_minutes} minutos y solo se puede usar una vez.\n"
        "Si no lo has pedido tú, ignora este correo: sin el enlace nadie "
        "puede entrar en tu cuenta.\n")


def _html(url: str, ttl_minutes: int) -> str:
    return (
        '<div style="font-family:system-ui,-apple-system,Segoe UI,sans-serif;'
        'max-width:520px;margin:0 auto;padding:24px;color:#111">'
        '<h2 style="margin:0 0 12px">Entra en ApuestaEdge</h2>'
        '<p style="color:#444;line-height:1.5">Pulsa el botón para acceder. '
        "El enlace caduca en "
        f"<b>{ttl_minutes} minutos</b> y solo sirve una vez.</p>"
        f'<p style="margin:24px 0"><a href="{url}" '
        'style="background:#16a34a;color:#fff;text-decoration:none;'
        'padding:12px 22px;border-radius:8px;font-weight:600;'
        'display:inline-block">Entrar en mi cuenta</a></p>'
        '<p style="color:#666;font-size:13px;line-height:1.5">Si el botón no '
        f'funciona, copia este enlace:<br><a href="{url}">{url}</a></p>'
        '<p style="color:#666;font-size:13px;line-height:1.5">Si no lo has '
        "pedido tú, ignora este correo: sin el enlace nadie puede entrar en "
        "tu cuenta.</p></div>")


def _send_smtp(to: str, subject: str, text: str, html: str) -> None:
    host = os.environ.get("SMTP_HOST", "").strip()
    if not host:
        raise RuntimeError("SMTP_HOST no configurado.")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    force_ssl = os.environ.get("SMTP_SSL", "").strip().lower() in {
        "1", "true", "yes", "on"} or port == 465
    context = ssl.create_default_context()

    message = EmailMessage()
    message["From"] = sender()
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text)
    message.add_alternative(html, subtype="html")

    if force_ssl:
        with smtplib.SMTP_SSL(host, port, timeout=20,
                              context=context) as smtp:
            if user:
                smtp.login(user, password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
            if user:
                smtp.login(user, password)
            smtp.send_message(message)


async def _send_resend(to: str, subject: str, text: str, html: str) -> None:
    key = os.environ.get("RESEND_API_KEY", "").strip()
    if not key:
        raise RuntimeError("RESEND_API_KEY no configurada.")
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            RESEND_API,
            headers={"Authorization": f"Bearer {key}"},
            json={"from": sender(), "to": [to], "subject": subject,
                  "text": text, "html": html})
        resp.raise_for_status()


async def send_login_link(to: str, url: str, ttl_minutes: int) -> None:
    """Envía el enlace de acceso. En modo ``console`` solo lo registra."""
    subject = _subject()
    text = _text(url, ttl_minutes)
    html = _html(url, ttl_minutes)
    kind = provider()
    if kind == "console":
        print(f"[apuesta_edge] enlace de acceso para {to}: {url}", flush=True)
        return
    if kind == "resend":
        await _send_resend(to, subject, text, html)
        return
    # smtplib es bloqueante: se ejecuta fuera del bucle de eventos.
    await asyncio.to_thread(_send_smtp, to, subject, text, html)
