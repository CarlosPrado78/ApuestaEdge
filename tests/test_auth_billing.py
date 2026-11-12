"""Tests de autenticación, gating del plan y cobros con Stripe."""

import hashlib
import hmac
import json
import time

import pytest
from fastapi.testclient import TestClient

from app import billing, db
from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ------------------------------------------------------------ modo demo
def test_register_login_and_me(client):
    r = client.post("/api/subscribe", json={"email": "ana@test.com", "plan": "free"})
    assert r.status_code == 200
    body = r.json()
    assert body["token"] and body["plan"] == "free"
    me = client.get("/api/auth/me", headers=_auth(body["token"])).json()
    assert me["authenticated"] and me["email"] == "ana@test.com"
    # Anónimo: sin sesión.
    assert client.get("/api/auth/me").json()["authenticated"] is False


def test_demo_premium_unlocks(client):
    """Sin claves de Stripe todo es demo y Premium se activa al instante."""
    r = client.post("/api/subscribe", json={"email": "luis@test.com",
                                            "plan": "premium"})
    body = r.json()
    assert body["mode"] == "demo" and body["activated"] is True
    assert body["plan"] == "premium"
    rec = client.get("/api/recommendations?plan=premium",
                     headers=_auth(body["token"]))
    assert rec.status_code == 200
    assert rec.json()["demo_mode"] is True
    assert rec.json()["count"] > 0


# ------------------------------------------------- bloqueo con Stripe activo
def test_stripe_lock_returns_402_without_subscription(client, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    assert billing.stripe_enabled()

    # Anónimo pidiendo premium -> 402.
    assert client.get("/api/recommendations?plan=premium").status_code == 402

    # Usuario free -> también 402.
    token = client.post("/api/auth/login",
                        json={"email": "free@test.com"}).json()["token"]
    assert client.get("/api/recommendations?plan=premium",
                      headers=_auth(token)).status_code == 402

    # Free sigue disponible para todos.
    free = client.get("/api/recommendations?plan=free")
    assert free.status_code == 200 and free.json()["count"] > 0


def test_checkout_flow_activates_only_after_webhook(client, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")

    async def fake_checkout(email: str, origin: str) -> str:
        return f"https://checkout.stripe.com/c/pay/test?email={email}"

    monkeypatch.setattr(billing, "create_checkout", fake_checkout)

    # La BD persiste entre ejecuciones: el usuario arranca en Free.
    raw = db.connect()
    try:
        db.set_user_plan(raw, "pago@test.com", "free")
    finally:
        raw.close()

    r = client.post("/api/subscribe", json={"email": "pago@test.com",
                                            "plan": "premium"})
    body = r.json()
    assert body["mode"] == "stripe" and body["checkout_url"].startswith("https://")
    assert body["plan"] == "free"  # el plan solicitado no se activa sin pago
    # Mientras no haya pago confirmado: sigue bloqueado.
    assert client.get("/api/recommendations?plan=premium",
                      headers=_auth(body["token"])).status_code == 402

    # Stripe confirma el pago por webhook.
    payload = json.dumps({
        "type": "checkout.session.completed",
        "data": {"object": {"metadata": {"email": "pago@test.com"}}},
    }).encode()
    ts = int(time.time())
    sig = hmac.new(b"whsec_test", f"{ts}.".encode() + payload,
                   hashlib.sha256).hexdigest()
    hook = client.post("/api/billing/webhook", content=payload,
                       headers={"Stripe-Signature": f"t={ts},v1={sig}"})
    assert hook.status_code == 200 and hook.json()["activated"] is True

    # Ahora sí: premium desbloqueado con la sesión del usuario.
    assert client.get("/api/recommendations?plan=premium",
                      headers=_auth(body["token"])).status_code == 200


def test_webhook_rejects_bad_signature(client, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    payload = b'{"type":"checkout.session.completed","data":{"object":{}}}'
    bad = client.post("/api/billing/webhook", content=payload,
                      headers={"Stripe-Signature": f"t={int(time.time())},v1={'0'*64}"})
    assert bad.status_code == 400
    sin_firma = client.post("/api/billing/webhook", content=payload)
    assert sin_firma.status_code == 400


def test_checkout_endpoint_requires_stripe_config(client):
    r = client.post("/api/billing/checkout", json={"email": "x@y.com"})
    assert r.status_code == 400  # sin claves: modo demo, no hay cobro


# ------------------------------------------------- verificación de firma
def test_signature_helper_roundtrip():
    secret = "whsec_abc"
    payload = b'{"a":1}'
    ts = int(time.time())
    sig = hmac.new(secret.encode(), f"{ts}.".encode() + payload,
                   hashlib.sha256).hexdigest()
    header = f"t={ts},v1={sig}"
    assert billing.verify_signature(payload, header, secret) is True
    # Payload alterado.
    assert billing.verify_signature(b'{"a":2}', header, secret) is False
    # Timestamp viejo (fuera de tolerancia).
    assert billing.verify_signature(payload, f"t={ts - 4000},v1={sig}",
                                    secret) is False
    # Cabecera vacía o secreto ausente.
    assert billing.verify_signature(payload, "", secret) is False
    assert billing.verify_signature(payload, header, "") is False


def test_email_extraction_from_event():
    event = {"type": "checkout.session.completed",
             "data": {"object": {"metadata": {"email": "A@B.com"}}}}
    assert billing.email_from_event(event) == "a@b.com"
    assert billing.email_from_event({"type": "other"}) is None
    assert billing.email_from_event(
        {"type": "checkout.session.completed",
         "data": {"object": {"customer_details": {"email": "c@d.com"}}}}) == "c@d.com"


def test_plans_and_health_expose_billing_mode(client):
    assert client.get("/api/plans").json()["billing"] == "demo"
    assert client.get("/api/health").json()["premium_locked"] is False


# ------------------------------------------- ciclo de vida de la suscripción
def _sign(payload: bytes) -> dict:
    ts = int(time.time())
    sig = hmac.new(b"whsec_test", f"{ts}.".encode() + payload,
                   hashlib.sha256).hexdigest()
    return {"Stripe-Signature": f"t={ts},v1={sig}"}


def _post_webhook(client, event: dict):
    return client.post("/api/billing/webhook",
                       content=json.dumps(event).encode(),
                       headers=_sign(json.dumps(event).encode()))


def test_subscription_lifecycle_activate_renew_deactivate(client, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    email = "ciclo@test.com"
    token = client.post("/api/auth/login", json={"email": email}).json()["token"]

    # 1) checkout completado -> Premium activo.
    ev1 = {"type": "checkout.session.completed",
           "data": {"object": {"id": "cs_test_1", "customer": "cus_1",
                               "subscription": "sub_1",
                               "metadata": {"email": email}}}}
    r = _post_webhook(client, ev1)
    assert r.status_code == 200 and r.json()["action"] == "activated"
    assert client.get("/api/recommendations?plan=premium",
                      headers=_auth(token)).status_code == 200
    st = client.get("/api/billing/subscription", headers=_auth(token)).json()
    assert st["plan"] == "premium" and st["has_stripe_customer"] is True
    assert st["can_manage"] is True

    # 2) renovación mensual (status active) -> sigue Premium.
    ev2 = {"type": "customer.subscription.updated",
           "data": {"object": {"id": "sub_1", "customer": "cus_1",
                               "status": "active",
                               "current_period_end": 1900000000,
                               "cancel_at_period_end": False}}}
    r = _post_webhook(client, ev2)
    assert r.json()["action"] == "renewed"
    st = client.get("/api/billing/subscription", headers=_auth(token)).json()
    assert st["plan"] == "premium" and st["current_period_end"]
    assert st["cancel_at_period_end"] is False

    # 3) el usuario programa la cancelación desde el portal de Stripe.
    ev3 = {"type": "customer.subscription.updated",
           "data": {"object": {"id": "sub_1", "customer": "cus_1",
                               "status": "active",
                               "current_period_end": 1900000000,
                               "cancel_at_period_end": True}}}
    assert _post_webhook(client, ev3).json()["action"] == "cancel_scheduled"
    st = client.get("/api/billing/subscription", headers=_auth(token)).json()
    assert st["cancel_at_period_end"] is True  # acceso hasta fin de periodo

    # 4) la suscripción termina (deleted) -> vuelve a Free.
    ev4 = {"type": "customer.subscription.deleted",
           "data": {"object": {"id": "sub_1", "customer": "cus_1",
                               "status": "canceled"}}}
    assert _post_webhook(client, ev4).json()["action"] == "deactivated"
    assert client.get("/api/recommendations?plan=premium",
                      headers=_auth(token)).status_code == 402
    st = client.get("/api/billing/subscription", headers=_auth(token)).json()
    assert st["plan"] == "free" and st["cancel_at_period_end"] is False


def test_webhook_ignores_unknown_users_and_events(client, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    ev = {"type": "customer.subscription.updated",
          "data": {"object": {"id": "sub_x", "customer": "cus_x",
                              "status": "active"}}}
    assert _post_webhook(client, ev).json()["action"] == "unknown_user"
    ev2 = {"type": "payment_intent.succeeded", "data": {"object": {}}}
    assert _post_webhook(client, ev2).json()["action"] == "ignored"


def test_portal_requires_auth_and_stripe_customer(client, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    # Sin sesión.
    r = client.post("/api/billing/portal", json={"email": "a@b.com"})
    assert r.status_code == 401
    # Sesión sin customer de Stripe.
    token = client.post("/api/auth/login",
                        json={"email": "portal@test.com"}).json()["token"]
    r = client.post("/api/billing/portal", json={"email": "portal@test.com"},
                    headers=_auth(token))
    assert r.status_code == 404
    # Modo demo: no hay portal.
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    r = client.post("/api/billing/portal", json={"email": "portal@test.com"},
                    headers=_auth(token))
    assert r.status_code == 400


def test_subscription_endpoint_anonymous(client):
    body = client.get("/api/billing/subscription").json()
    assert body["authenticated"] is False
    assert body["billing"] == "demo"


# ------------------------------------------------ regresiones de cuenta/plan
def test_login_keeps_existing_premium_plan(client):
    """Volver a iniciar sesión NUNCA degrada a Free a quien ya pagó."""
    email = "premium-login@test.com"
    first = client.post("/api/auth/login", json={"email": email}).json()
    assert first["plan"] == "free"

    conn = db.connect()
    try:
        db.set_user_plan(conn, email, "premium")
    finally:
        conn.close()

    again = client.post("/api/auth/login", json={"email": email}).json()
    assert again["plan"] == "premium"
    me = client.get("/api/auth/me", headers=_auth(again["token"])).json()
    assert me["authenticated"] is True and me["plan"] == "premium"


def test_recommendations_use_account_plan_by_default(client, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    email = "auto-plan@test.com"
    token = client.post("/api/auth/login", json={"email": email}).json()["token"]

    free = client.get("/api/recommendations", headers=_auth(token)).json()
    assert free["plan"] == "free" and free["min_edge"] == 0.06

    conn = db.connect()
    try:
        db.set_user_plan(conn, email, "premium")
    finally:
        conn.close()

    premium = client.get("/api/recommendations", headers=_auth(token)).json()
    assert premium["plan"] == "premium"
    assert premium["min_edge"] == 0.03
    assert premium["count"] > free["count"]


def _fake_stripe_session(email: str, *, paid: bool = True):
    async def fake_session(session_id: str) -> dict:
        return {"id": session_id,
                "status": "complete" if paid else "open",
                "payment_status": "paid" if paid else "unpaid",
                "customer": "cus_confirm",
                "subscription": "sub_confirm",
                "metadata": {"email": email}}

    async def fake_subscription(subscription_id: str) -> dict:
        return {"id": subscription_id, "status": "active",
                "current_period_end": 1900000000,
                "cancel_at_period_end": False}

    return fake_session, fake_subscription


def test_confirm_checkout_activates_without_webhook(client, monkeypatch):
    """Al volver de Stripe se activa Premium verificando la sesión."""
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    email = "confirm@test.com"
    fake_session, fake_sub = _fake_stripe_session(email)
    monkeypatch.setattr(billing, "retrieve_checkout_session", fake_session)
    monkeypatch.setattr(billing, "retrieve_subscription", fake_sub)

    r = client.post("/api/billing/confirm",
                    json={"session_id": "cs_test_123"})
    assert r.status_code == 200
    body = r.json()
    assert body["activated"] is True and body["plan"] == "premium"
    assert body["token"]

    me = client.get("/api/auth/me", headers=_auth(body["token"])).json()
    assert me["plan"] == "premium"
    st = client.get("/api/billing/subscription",
                    headers=_auth(body["token"])).json()
    assert st["has_stripe_customer"] is True and st["can_manage"] is True


def test_confirm_checkout_does_not_activate_unpaid(client, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    fake_session, fake_sub = _fake_stripe_session("nopago@test.com", paid=False)
    monkeypatch.setattr(billing, "retrieve_checkout_session", fake_session)
    monkeypatch.setattr(billing, "retrieve_subscription", fake_sub)

    r = client.post("/api/billing/confirm",
                    json={"session_id": "cs_test_unpaid"})
    assert r.status_code == 200
    assert r.json()["activated"] is False
    me = client.get("/api/auth/me", headers={
        "Authorization": "Bearer inexistente"}).json()
    assert me["authenticated"] is False


def test_logout_clears_auth_cookie(client):
    email = "logout@test.com"
    token = client.post("/api/auth/login", json={"email": email}).json()["token"]
    client.cookies.set("ae_token", token)
    r = client.post("/api/auth/logout")
    assert r.status_code == 200 and r.json()["ok"] is True
    # La respuesta pide borrar la cookie de sesión.
    assert "ae_token=" in r.headers.get("set-cookie", "")
