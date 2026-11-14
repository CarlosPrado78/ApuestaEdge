"""Métricas del foso: picks cerrados y verificaciones de hash en /api/health."""

import pytest
from fastapi.testclient import TestClient

from app import db, ledger
from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _rec(event_id: str, event: str) -> dict:
    return {
        "match_id": event_id,
        "sport_key": "basketball_nba",
        "sport": "basketball",
        "league": "NBA · USA",
        "league_raw": "NBA · USA",
        "event": event,
        "market_type": "h2h",
        "selection": "away",
        "selection_label": "Victoria de Celtics",
        "bookmaker": "Pinnacle",
        "odds": 1.85,
        "model_prob": 0.58,
        "market_prob": 0.54,
        "edge": 0.042,
        "kelly": {"stake_pct": 1.5},
        "commence_time": "2026-12-01T20:00:00Z",
        "home_team": "Lakers",
        "away_team": "Celtics",
    }


def test_health_includes_closed_picks_and_verifications(client):
    body = client.get("/api/health").json()
    assert body["picks_cerrados"] == 0
    assert body["verificaciones_hash"] == 0


def test_health_counts_closed_picks(client):
    conn = db.connect()
    try:
        ledger.append_pick(conn, _rec("m-closed-1", "Lakers vs Celtics"))
        ledger.append("pick_closings", conn, {
            "pick_id": 1, "closing_odds": 1.80, "closing_at": 1.0,
            "clv_pct": 2.5})
        ledger.append("pick_results", conn, {
            "pick_id": 1, "result": "won", "profit_units": 0.85,
            "settled_at": 2.0})
    finally:
        conn.close()
    body = client.get("/api/health").json()
    assert body["picks_cerrados"] == 1


def test_verify_report_increments_counter(client):
    for ok in (True, True, False):
        r = client.post("/api/verify/report", json={"ok": ok, "scope": "pick"})
        assert r.status_code == 200, r.text
    body = client.get("/api/health").json()
    assert body["verificaciones_hash"] == 3


def test_verify_report_is_public_and_validates_body(client):
    # Sin autenticación (el usuario no tiene sesión para verificar).
    assert client.post("/api/verify/report",
                       json={"ok": True}).status_code == 200
    # Cuerpo malformado → 422, no 500.
    assert client.post("/api/verify/report", json={"ok": "si"}).status_code == 422
