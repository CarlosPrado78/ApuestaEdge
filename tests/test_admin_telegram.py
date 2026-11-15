"""Opción A (/api/health → telegram) y Opción B (POST /api/admin/telegram-test)."""

import pytest
from fastapi.testclient import TestClient

from app import config, notifier
from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _set_telegram(monkeypatch, token: str, chat: str) -> None:
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", token)
    monkeypatch.setattr(config, "TELEGRAM_BROADCAST_CHAT", chat)


# ------------------------------------------------------- Opción A: /api/health
def test_health_telegram_all_false_when_unset(client, monkeypatch):
    _set_telegram(monkeypatch, "", "")
    body = client.get("/api/health")
    assert body.status_code == 200
    assert body.json()["telegram"] == {
        "configured": False, "chat_id_set": False, "token_set": False}


def test_health_telegram_configured_true_when_both_set(client, monkeypatch):
    _set_telegram(monkeypatch, "123456:ABC-secret-token", "-100123456")
    body = client.get("/api/health")
    assert body.status_code == 200
    assert body.json()["telegram"] == {
        "configured": True, "chat_id_set": True, "token_set": True}


def test_health_telegram_partial_config_is_not_configured(client, monkeypatch):
    # Solo token: configured debe ser False aunque token_set sea True.
    _set_telegram(monkeypatch, "123456:ABC-secret-token", "")
    tg = client.get("/api/health").json()["telegram"]
    assert tg == {"configured": False, "chat_id_set": False, "token_set": True}
    # Solo chat_id.
    _set_telegram(monkeypatch, "", "-100123456")
    tg = client.get("/api/health").json()["telegram"]
    assert tg == {"configured": False, "chat_id_set": True, "token_set": False}


def test_health_never_leaks_telegram_secrets(client, monkeypatch):
    token, chat = "999999:ZZZ-super-secreto", "-99887766"
    _set_telegram(monkeypatch, token, chat)
    raw = client.get("/api/health").text
    assert token not in raw
    assert chat not in raw
    # Y los valores no aparecen en ninguna clave del JSON.
    assert set(client.get("/api/health").json()["telegram"]) == {
        "configured", "chat_id_set", "token_set"}


# -------------------------------------------- Opción B: /api/admin/telegram-test
def _admin_headers(value: str = "tok-test-123") -> dict:
    return {"X-Admin-Token": value}


def test_telegram_test_401_without_header(client, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_TOKEN", "correct-admin-token-abc")
    r = client.post("/api/admin/telegram-test")
    assert r.status_code == 401
    assert r.json() == {"error": "unauthorized"}


def test_telegram_test_401_with_wrong_header(client, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_TOKEN", "correct-admin-token-abc")
    r = client.post("/api/admin/telegram-test",
                    headers=_admin_headers("otro-token"))
    assert r.status_code == 401
    assert r.json() == {"error": "unauthorized"}


def test_telegram_test_401_when_admin_token_unset(client, monkeypatch):
    # Sin ADMIN_TOKEN en el entorno, el endpoint está cerrado para todos.
    monkeypatch.setattr(config, "ADMIN_TOKEN", "")
    r = client.post("/api/admin/telegram-test",
                    headers=_admin_headers("cualquiera"))
    assert r.status_code == 401
    assert r.json() == {"error": "unauthorized"}


def test_telegram_test_400_when_telegram_not_configured(client, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_TOKEN", "correct-admin-token-abc")
    _set_telegram(monkeypatch, "", "")
    r = client.post("/api/admin/telegram-test",
                    headers=_admin_headers("correct-admin-token-abc"))
    assert r.status_code == 400
    body = r.json()
    assert body["error"] == "telegram_not_configured"
    assert body["telegram"] == {
        "configured": False, "chat_id_set": False, "token_set": False}


def test_telegram_test_200_with_mocked_send(client, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_TOKEN", "correct-admin-token-abc")
    _set_telegram(monkeypatch, "123456:ABC-secret", "-100123456")
    seen = {}

    async def fake_send(chat_id, text, *, timeout=10.0):
        seen.update(chat_id=chat_id, text=text, timeout=timeout)
        return 4242, ""

    monkeypatch.setattr(notifier, "send_message_with_id", fake_send)
    r = client.post("/api/admin/telegram-test",
                    headers=_admin_headers("correct-admin-token-abc"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["message_id"] == 4242
    assert "T" in body["sent_at"]  # timestamp ISO
    # Mensaje exigido: texto + timestamp ISO; timeout de 10 s.
    assert seen["text"].startswith("Test de ApuestaEdge desde Render — ")
    assert seen["chat_id"] == "-100123456"
    assert seen["timeout"] == 10.0
    # El token jamás viaja en el texto del mensaje.
    assert "123456:ABC-secret" not in seen["text"]


def test_telegram_test_502_when_telegram_rejects(client, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_TOKEN", "correct-admin-token-abc")
    _set_telegram(monkeypatch, "123456:ABC-secret", "-100123456")

    async def fake_send(chat_id, text, *, timeout=10.0):
        return None, "Bad Request: chat not found"

    monkeypatch.setattr(notifier, "send_message_with_id", fake_send)
    r = client.post("/api/admin/telegram-test",
                    headers=_admin_headers("correct-admin-token-abc"))
    assert r.status_code == 502
    assert r.json() == {"ok": False, "error": "Bad Request: chat not found"}


def test_telegram_test_never_leaks_token_in_response(client, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_TOKEN", "correct-admin-token-abc")
    token = "123456:ABC-super-secreto"
    _set_telegram(monkeypatch, token, "-100123456")

    async def fake_send(chat_id, text, *, timeout=10.0):
        # Telegram "rechaza" con un error que, sin saneado, podría
        # contener la URL (que lleva el token dentro).
        return None, f"HTTP 400 url=https://api.telegram.org/bot{token}/sendMessage"

    monkeypatch.setattr(notifier, "send_message_with_id", fake_send)
    r = client.post("/api/admin/telegram-test",
                    headers=_admin_headers("correct-admin-token-abc"))
    assert r.status_code == 502
    assert token not in r.text
    assert "***" in r.text  # el token aparece saneado, no en claro


def test_send_message_with_id_scrubs_token_on_http_error(monkeypatch):
    """El saneado real de notifier: token y chat_id nunca salen en claro."""
    import httpx

    token = "777:SECRET-token"
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", token)

    class BoomClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, **k):
            raise httpx.ConnectError(f"falló {url}")

    monkeypatch.setattr(httpx, "AsyncClient", BoomClient)
    import asyncio
    msg_id, err = asyncio.run(
        notifier.send_message_with_id("-100555", "hola"))
    assert msg_id is None
    assert token not in err
    assert "***" in err


def test_telegram_test_hidden_from_openapi(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/admin/telegram-test" not in paths
    # Y sigue accesible en la app (solo oculto del esquema).
    assert client.post("/api/admin/telegram-test").status_code == 401
