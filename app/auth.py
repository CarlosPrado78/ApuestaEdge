"""Autenticación por token de sesión + contraseña.

El plan real vive en la tabla ``users`` (no en un query param): por eso
``?plan=premium`` solo funciona en modo demo. Al conectar Stripe el plan
se activa desde el webhook del checkout.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets

from fastapi import Request

from . import db

COOKIE_NAME = "ae_token"
BEARER_PREFIX = "Bearer "

# Parámetros de derivación de contraseña (PBKDF2-SHA256). Se guardan en el
# hash para poder cambiarlos en el futuro sin romper cuentas existentes.
_PBKDF2_ITERATIONS = 100_000
_PBKDF2_SALT_BYTES = 16


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


def hash_password(password: str) -> str:
    """Deriva la contraseña con PBKDF2-SHA256 + sal aleatoria.

    Formato: ``pbkdf2:sha256:<iteraciones>$<sal_hex>$<hash_hex>``.
    """
    salt = secrets.token_bytes(_PBKDF2_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return (f"pbkdf2:sha256:{_PBKDF2_ITERATIONS}$"
            f"{salt.hex()}${digest.hex()}")


def verify_password(password: str, stored: str | None) -> bool:
    """Verifica una contraseña contra el hash almacenado (tiempo constante)."""
    if not stored or "$" not in stored:
        return False
    try:
        header, salt_hex, hash_hex = stored.split("$", 2)
        algo, _, iterations = header.split(":", 2)
        if algo != "pbkdf2" or _ != "sha256":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False
