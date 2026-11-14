"""Tests del módulo de alertas por Telegram (formato, comandos, dedupe)."""

import pytest
from fastapi.testclient import TestClient

from app import config, db, notifier
from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _sample_pick(plan: str = "premium") -> dict:
    return {
        "match_id": "demo-002", "sport": "soccer",
        "league": "Premier League · Inglaterra",
        "commence_time": "2026-11-15T16:30:00Z",
        "home_team": "Manchester City", "away_team": "Liverpool",
        "selection_label": "Victoria de Manchester City",
        "odds": 2.60, "bookmaker": "888sport",
        "edge": 0.066, "ev": 0.151, "confidence": 0.84,
        "model_prob": 0.443, "market_prob": 0.377,
        "kelly": {"stake_pct": 2.36, "stake_units": 23.63,
                  "kelly_full_pct": 9.45, "kelly_fraction_used": 0.25},
        "explanation": {"summary": "«Victoria de Manchester City» a 2.60 ofrece +15.1% de EV."},
    }


# ------------------------------------------------------------- formato
def test_format_pick_premium_contains_the_numbers():
    msg = notifier.format_pick(_sample_pick("premium"), "premium", bankroll=1000)
    assert "Manchester City" in msg and "Liverpool" in msg
    assert "+6.6%" in msg and "+15.1%" in msg and "84%" in msg
    assert "2.60" in msg and "888sport" in msg
    assert "Stake Kelly" in msg and "23.63" in msg
    assert msg.count("<b>") >= 4  # formato HTML para Telegram


def test_format_pick_free_hides_stake():
    msg = notifier.format_pick(_sample_pick(), "free")
    assert "Stake Kelly" not in msg
    assert "🔒" in msg and "Premium" in msg
    assert "+6.6%" in msg  # el edge sí se muestra en Free


def test_format_pick_escapes_html():
    pick = _sample_pick()
    pick["home_team"] = "<script>alert(1)</script>"
    pick["league"] = 'Liga & "campeones"'
    msg = notifier.format_pick(pick, "premium")
    assert "<script>" not in msg
    assert "&lt;script&gt;" in msg
    assert "&amp;" in msg


def test_format_digest_batches_picks():
    digest = notifier.format_digest([_sample_pick(), _sample_pick()],
                                    "premium")
    assert "2 picks con valor" in digest


# ------------------------------------------------------------- comandos
def test_start_links_account_and_stop_unlinks():
    conn = db.connect()
    try:
        db.create_user(conn, "tg1@test.com", plan="premium")
        code = db.ensure_link_code(conn, "tg1@test.com")
        chat = "999001"

        answers = notifier.process_update(
            {"message": {"chat": {"id": chat}, "text": f"/start {code}"}}, conn)
        assert len(answers) == 1 and "vinculada" in answers[0][1]
        assert db.user_by_chat(conn, chat)["email"] == "tg1@test.com"

        status = notifier.process_update(
            {"message": {"chat": {"id": chat}, "text": "/status"}}, conn)
        assert "Premium" in status[0][1] and "alertas: activas" in status[0][1].lower()

        stop = notifier.process_update(
            {"message": {"chat": {"id": chat}, "text": "/stop"}}, conn)
        assert "desactivadas" in stop[0][1]
        assert db.user_by_chat(conn, chat) is None
    finally:
        conn.close()


def test_start_with_bad_code_shows_help():
    answers = notifier.process_update(
        {"message": {"chat": {"id": "999002"}, "text": "/start codigo_malo"}})
    assert "inválido" in answers[0][1]


def test_unknown_command_and_empty_update():
    assert notifier.process_update({}) == []
    answer = notifier.process_update(
        {"message": {"chat": {"id": "999003"}, "text": "hola"}})
    assert "ApuestaEdge" in answer[0][1]  # mensaje de ayuda


def test_mis_picks_returns_value_or_honest_fallback():
    conn = db.connect()
    try:
        db.create_user(conn, "tg2@test.com", plan="premium")
        code = db.ensure_link_code(conn, "tg2@test.com")
        notifier.process_update(
            {"message": {"chat": {"id": "999004"}, "text": f"/start {code}"}}, conn)
        answer = notifier.process_update(
            {"message": {"chat": {"id": "999004"}, "text": "/mis_picks"}}, conn)
        text = answer[0][1]
        # La demo tiene 4 picks con edge ≥ 4%: llega el digest con cifras.
        assert ("picks con valor" in text or "no hay apuestas" in text)
        if "picks con valor" in text:
            assert "Edge" in text and "EV" in text
    finally:
        conn.close()


# --------------------------------------------------------------- dedupe
def test_alert_dedupe_never_repeats_a_pick():
    conn = db.connect()
    try:
        db.alerts_reset(conn, "777001")
        first = db.alert_mark_sent(conn, "777001", "demo-002", "home", 0.06)
        second = db.alert_mark_sent(conn, "777001", "demo-002", "home", 0.06)
        other = db.alert_mark_sent(conn, "777001", "demo-002", "away", 0.05)
        assert first is True and second is False and other is True
    finally:
        conn.close()


def test_send_message_without_token_fails_cleanly(monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "")
    import asyncio
    ok, err = asyncio.run(notifier.send_message("1", "hola"))
    assert ok is False and "no configurado" in err


def test_send_digest_uses_one_market_fetch_per_cycle(monkeypatch):
    """Con N suscriptores se pide el parte UNA vez, no N (créditos)."""
    import asyncio

    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "1:x")
    conn = db.connect()
    try:
        for i, email in enumerate(("uno@test.com", "dos@test.com")):
            db.create_user(conn, email)
            code = db.ensure_link_code(conn, email)
            db.link_telegram(conn, code, f"chat{i}")
    finally:
        conn.close()

    calls = {"provider": 0, "sent": 0}

    def provider():
        calls["provider"] += 1
        return [], "unavailable"

    pick = {"match_id": "m1", "selection": "home", "sport": "soccer",
            "league": "NBA · USA", "home_team": "A", "away_team": "B",
            "selection_label": "A gana", "odds": 2.0, "bookmaker": "x",
            "edge": 0.06, "ev": 0.1, "confidence": 0.8,
            "model_prob": 0.55, "market_prob": 0.5, "commence_time": "2026-11-15T00:00:00Z",
            "explanation": {"summary": "ok"}}
    monkeypatch.setattr(notifier.service, "build_recommendations",
                        lambda **kw: {"picks": [pick]})

    async def fake_send(chat_id, text, client=None):
        calls["sent"] += 1
        return True, ""

    monkeypatch.setattr(notifier, "send_message", fake_send)
    sent = asyncio.run(
        notifier.TelegramNotifier(matches_provider=provider).send_digest())

    assert calls["provider"] == 1  # un solo parte para los dos suscriptores
    assert sent == 2 and calls["sent"] == 2



# --------------------------------------------------------------- API
def test_telegram_status_anonymous(client):
    body = client.get("/api/telegram").json()
    assert body["configured"] is False
    assert body["authenticated"] is False
    assert body["deep_link"] is None


def test_telegram_status_returns_link_code_for_users(client):
    client.post("/api/auth/register",
                json={"email": "tgapi@test.com", "password": "secret123"})
    token = client.post("/api/auth/login",
                        json={"email": "tgapi@test.com",
                              "password": "secret123"}).json()["token"]
    body = client.get("/api/telegram", headers=_auth(token)).json()
    assert body["authenticated"] is True
    assert body["link_code"] and len(body["link_code"]) >= 6


def test_telegram_deep_link_with_username(client, monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setattr(config, "TELEGRAM_BOT_USERNAME", "apuesta_edge_bot")
    client.post("/api/auth/register",
                json={"email": "tgapi2@test.com", "password": "secret123"})
    token = client.post("/api/auth/login",
                        json={"email": "tgapi2@test.com",
                              "password": "secret123"}).json()["token"]
    body = client.get("/api/telegram", headers=_auth(token)).json()
    assert body["configured"] is True
    assert body["deep_link"].startswith("https://t.me/apuesta_edge_bot?start=")
    assert body["link_code"] in body["deep_link"]


def test_broadcast_test_is_closed_without_admin_token(client):
    # Sin ADMIN_TOKEN la ruta queda deshabilitada para todo el mundo.
    assert client.post("/api/telegram/broadcast-test").status_code == 403


def test_broadcast_test_rejects_wrong_token(client, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_TOKEN", "s3cret-admin")
    assert client.post("/api/telegram/broadcast-test").status_code == 401
    assert client.post("/api/telegram/broadcast-test",
                       headers={"Authorization": "Bearer nope"}).status_code == 401


def test_broadcast_test_with_admin_token_needs_telegram(client, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_TOKEN", "s3cret-admin")
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "")
    r = client.post("/api/telegram/broadcast-test",
                    headers={"Authorization": "Bearer s3cret-admin"})
    assert r.status_code == 400


def test_mis_picks_requires_linked_chat():
    update = {"update_id": 1, "message": {"chat": {"id": 424242},
                                          "text": "/mis_picks"}}
    replies = notifier.process_update(update)
    assert len(replies) == 1
    chat_id, text = replies[0]
    assert chat_id == "424242"
    assert "vinculado" in text and "/start" in text


def test_reset_alerts_requires_auth(client):
    r = client.post("/api/telegram/reset-alerts", json={"email": "x@y.com"})
    assert r.status_code == 401


# --------------------------------------------------- reglas configurables (/alertas)
def test_pick_matches_rule_filters_league_edge_odds_market_and_time():
    pick = _sample_pick("premium")
    pick["market"] = "h2h"
    pick["event_start"] = 2000.0
    base_rule = {
        "enabled": True, "plan": "premium",
        "leagues": ["Premier League · Inglaterra"],
        "edge_min": 0.05, "odds_min": 2.0, "odds_max": 3.0,
        "markets": ["h2h"], "max_minutes_to_start": 30,
    }
    assert notifier.pick_matches_rule(pick, base_rule, now=1000.0) is True
    # Liga distinta -> no coincide
    assert notifier.pick_matches_rule(
        pick, {**base_rule, "leagues": ["LaLiga · España"]}, now=1000.0) is False
    # Rango de cuota fuera -> no coincide
    assert notifier.pick_matches_rule(
        pick, {**base_rule, "odds_max": 2.20}, now=1000.0) is False
    # Mercado fuera -> no coincide
    assert notifier.pick_matches_rule(
        pick, {**base_rule, "markets": ["outright"]}, now=1000.0) is False
    # Demasiado lejos del inicio (> 30 min = 1800 s) -> no coincide
    assert notifier.pick_matches_rule(
        pick, base_rule, now=100.0) is False
    # Regla pausada -> no coincide
    assert notifier.pick_matches_rule(
        pick, {**base_rule, "enabled": False}, now=1000.0) is False


def test_alert_rules_crud_pause_resume_and_plan_limits(client):
    email = "rules_user@test.com"
    client.post("/api/auth/register",
                json={"email": email, "password": "secret123"})
    token = client.post("/api/auth/login",
                        json={"email": email, "password": "secret123"}).json()["token"]

    # Free: edge_min se ajusta al mínimo del plan (6%) y permite máx 1 regla.
    r1 = client.post("/api/alerts/rules", headers=_auth(token), json={
        "name": "Mi regla Free",
        "leagues": ["LaLiga · España"],
        "edge_min": 0.04,
        "odds_min": 1.50,
        "odds_max": 3.20,
        "markets": ["h2h"],
        "max_minutes_to_start": 180,
        "channel_email": True,
        "channel_telegram": False,
    })
    assert r1.status_code == 200
    rule = r1.json()["rule"]
    assert rule["edge_min"] == pytest.approx(0.06)
    assert rule["enabled"] is True

    # Segunda regla en Free -> 403
    r2 = client.post("/api/alerts/rules", headers=_auth(token), json={
        "name": "Segunda regla", "edge_min": 0.06,
        "odds_min": 1.5, "odds_max": 3.0,
    })
    assert r2.status_code == 403

    # Pausar y reanudar
    paused = client.patch(f"/api/alerts/rules/{rule['id']}",
                          headers=_auth(token), json={"enabled": False})
    assert paused.status_code == 200 and paused.json()["rule"]["enabled"] is False
    resumed = client.patch(f"/api/alerts/rules/{rule['id']}",
                           headers=_auth(token), json={"enabled": True})
    assert resumed.status_code == 200 and resumed.json()["rule"]["enabled"] is True

    # Eliminar
    deleted = client.delete(f"/api/alerts/rules/{rule['id']}", headers=_auth(token))
    assert deleted.status_code == 200
    listed = client.get("/api/alerts/rules", headers=_auth(token)).json()
    assert listed["rules"] == []


def test_alert_rules_dispatch_dedupe_and_non_affiliate_links(monkeypatch):
    import asyncio
    conn = db.connect()
    try:
        email = "dispatch@test.com"
        db.create_user(conn, email, plan="premium")
        code = db.ensure_link_code(conn, email)
        db.link_telegram(conn, code, "chat-rule-1")
        rule = db.alert_rule_create(
            conn, email, name="Premier ≥ 5%",
            leagues=["Premier League · Inglaterra"],
            edge_min=0.05, odds_min=1.80, odds_max=3.20,
            markets=["h2h"], max_minutes_to_start=None,
            channel_email=True, channel_telegram=True)

        pick = _sample_pick("premium")
        pick["selection"] = "home"
        pick["market"] = "h2h"
        monkeypatch.setattr(notifier.service, "build_recommendations",
                            lambda **kw: {"picks": [pick]})

        tg_messages = []

        async def fake_send(chat_id, text, client=None):
            tg_messages.append((chat_id, text))
            return True, ""

        monkeypatch.setattr(notifier, "send_message", fake_send)

        first = asyncio.run(notifier.dispatch_alert_rules(conn))
        assert first["sent"] == 2
        assert first["email"] == 1 and first["telegram"] == 1
        assert len(tg_messages) == 1
        assert "sin afiliado" in tg_messages[0][1]
        assert "https://www.888sport.com" in tg_messages[0][1]

        # Segunda pasada: dedupe por (regla, canal, partido, selección)
        second = asyncio.run(notifier.dispatch_alert_rules(conn))
        assert second["sent"] == 0

        deliveries = db.alert_deliveries_for_user(conn, email)
        assert len(deliveries) == 2
        assert {d["channel"] for d in deliveries} == {"email", "telegram"}
        assert rule["id"] == deliveries[0]["rule_id"]
    finally:
        conn.close()


def test_alerts_page_is_public_and_clean(client):
    page = client.get("/alertas")
    assert page.status_code == 200
    assert "/alertas.js" in page.text
    assert "sin código de afiliado" in page.text
    assert "The Odds API" not in page.text
    assert "ODDS_API_KEY" not in page.text
