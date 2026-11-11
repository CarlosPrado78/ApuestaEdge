"""Cobros con Stripe (Checkout + webhook) y bandera de bloqueo del plan.

Activación:

    export STRIPE_SECRET_KEY='sk_test_...'          # claves de prueba
    export STRIPE_WEBHOOK_SECRET='whsec_...'        # firma del webhook

Sin claves la app corre en **modo demo**: el plan Premium se otorga al
instante (clearmente etiquetado como demo) para poder probar el flujo.

Con claves, ``stripe_enabled()`` activa el **bloqueo estricto**:
``plan=premium`` exige una sesión de usuario con plan premium real, y el
plan solo se activa cuando Stripe confirma el pago por webhook.

La API de Stripe se llama con ``httpx`` (sin SDK) para mantener las
dependencias mínimas.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time

import httpx

from . import config

STRIPE_API = "https://api.stripe.com/v1"
SIGNATURE_HEADER = "Stripe-Signature"
_TOLERANCE_SECONDS = 300


def stripe_secret() -> str:
    return os.environ.get("STRIPE_SECRET_KEY", "").strip()


def webhook_secret() -> str:
    return os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()


def stripe_enabled() -> bool:
    """True => el plan Premium se bloquea y se cobra de verdad."""
    return bool(stripe_secret())


def premium_cents() -> int:
    return int(config.PLANS["premium"]["price_usd"] * 100)


async def create_checkout(email: str, origin: str,
                          timeout: float = 15.0) -> str:
    """Sesión de Checkout de Stripe para el plan Premium (1 mes)."""
    data = {
        "mode": "subscription",
        "customer_email": email,
        "line_items[0][quantity]": "1",
        "line_items[0][price_data][currency]": "usd",
        "line_items[0][price_data][unit_amount]": str(premium_cents()),
        "line_items[0][price_data][recurring][interval]": "month",
        "line_items[0][price_data][product_data][name]": "ApuestaEdge Premium",
        "success_url": f"{origin}/?suscripcion=ok",
        "cancel_url": f"{origin}/#precios",
        "metadata[email]": email,
        # El email viaja también en la suscripción: los eventos de ciclo de
        # vida (updated/deleted) lo traen en metadata y así podemos
        # localizar al usuario aunque no guardemos el customer id.
        "subscription_data[metadata][email]": email,
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{STRIPE_API}/checkout/sessions",
            data=data,
            headers={"Authorization": f"Bearer {stripe_secret()}"})
        resp.raise_for_status()
        url = resp.json().get("url")
        if not url:
            raise RuntimeError("Stripe no devolvió URL de checkout")
        return str(url)


def verify_signature(payload: bytes, header: str, secret: str,
                     now: float | None = None) -> bool:
    """Verificación de ``Stripe-Signature`` (esquema v1 de Stripe)."""
    if not header or not secret:
        return False
    timestamp = None
    candidates = []
    for part in header.split(","):
        key, _, value = part.strip().partition("=")
        if key == "t":
            try:
                timestamp = int(value)
            except ValueError:
                return False
        elif key == "v1":
            candidates.append(value)
    if timestamp is None or not candidates:
        return False
    current = time.time() if now is None else now
    if abs(current - timestamp) > _TOLERANCE_SECONDS:
        return False
    signed = f"{timestamp}.".encode() + payload
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, c) for c in candidates)


def email_from_event(event: dict) -> str | None:
    """Email del comprador en un evento de checkout (si lo trae)."""
    if event.get("type") != "checkout.session.completed":
        return None
    obj = (event.get("data") or {}).get("object") or {}
    email = ((obj.get("metadata") or {}).get("email")
             or (obj.get("customer_details") or {}).get("email")
             or obj.get("customer_email"))
    return str(email).strip().lower() if email else None


def subscription_from_event(event: dict) -> dict | None:
    """Extrae el estado de la suscripción de un evento de ciclo de vida.

    Devuelve ``{customer_id, subscription_id, status, period_end,
    cancel_at_period_end, email}`` o ``None`` si el evento no aplica.
    """
    etype = event.get("type", "")
    if etype not in ("customer.subscription.updated",
                     "customer.subscription.deleted",
                     "checkout.session.completed"):
        return None
    obj = (event.get("data") or {}).get("object") or {}
    sub_id = obj.get("id") if etype.startswith("customer.") else obj.get("subscription")
    if etype.startswith("customer.") and not str(sub_id or "").startswith("sub_"):
        return None
    if etype == "checkout.session.completed":
        # En la sesión de checkout el campo `status` es "complete"; la
        # suscripción recién creada siempre está activa al confirmarse.
        status = "active"
    else:
        status = str(obj.get("status") or "")
    email = ((obj.get("metadata") or {}).get("email")
             or (obj.get("customer_details") or {}).get("email")
             or obj.get("customer_email"))
    return {
        "customer_id": str(obj.get("customer") or ""),
        "subscription_id": str(sub_id or ""),
        "status": str(status),
        "period_end": float(obj.get("current_period_end") or 0) or None,
        "cancel_at_period_end": bool(obj.get("cancel_at_period_end")),
        "email": str(email).strip().lower() if email else None,
    }


# Estados de suscripción de Stripe que mantienen el acceso Premium.
ACTIVE_SUB_STATUSES = ("active", "trialing")


async def create_portal_session(customer_id: str, origin: str,
                                timeout: float = 15.0) -> str:
    """Sesión del Cliente de Stripe (ver cupones, cancelar, cambiar tarjeta)."""
    data = {
        "customer": customer_id,
        "return_url": f"{origin}/#precios",
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{STRIPE_API}/billing_portal/sessions",
            data=data,
            headers={"Authorization": f"Bearer {stripe_secret()}"})
        resp.raise_for_status()
        url = resp.json().get("url")
        if not url:
            raise RuntimeError("Stripe no devolvió URL del portal")
        return str(url)


def parse_event(payload: bytes) -> dict:
    return json.loads(payload)
