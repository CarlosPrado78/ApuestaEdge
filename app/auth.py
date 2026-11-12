"""Autenticación ligera por token y resolución del plan del usuario.

Sin dependencias externas: token aleatorio por usuario, enviado como
``Authorization: Bearer <token>`` o cookie ``ae_token``.

El plan real vive aquí (tabla ``users``), no en un query param: por eso
``?plan=premium`` solo funciona en modo demo. Al conectar Stripe el plan
se activa desde el webhook del checkout.
"""

from __future__ import annotations

from fastapi import Request

from . import db

COOKIE_NAME = "ae_token"
BEARER_PREFIX = "Bearer "


def token_from_request(request: Request) -> str | None:
    auth_header = request.headers.get("authorization") or ""
    if auth_header.startswith(BEARER_PREFIX):
        token = auth_header[len(BEARER_PREFIX):].strip()
        if token:
            return token
    return request.cookies.get(COOKIE_NAME)


def user_from_request(request: Request) -> dict | None:
    """Usuario activo o None (modo anónimo)."""
    token = token_from_request(request)
    if not token:
        return None
    conn = db.connect()
    try:
        return db.get_user_by_token(conn, token)
    finally:
        conn.close()


def is_premium(request: Request) -> bool:
    user = user_from_request(request)
    return bool(user and user.get("plan") == "premium")


def origin_of(request: Request) -> str:
    """Origen público (para URLs de retorno de Stripe)."""
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    return str(request.headers.get("origin") or f"{proto}://{request.url.netloc}")


def server_origin(request: Request) -> str:
    """Origen público derivado del Host (no de Origin, controlado por el cliente)."""
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host") or request.url.netloc
    return f"{proto}://{host}".rstrip("/")
