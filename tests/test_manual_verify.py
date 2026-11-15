"""Campo manual de verificación de hash en /verify/1 (caso negativo incluido).

La comprobación real ocurre en cliente (crypto.subtle en pick.js); aquí se
cubre que la superficie se sirva con el campo, las cadenas i18n ES/EN y la
lógica de comparación (hash incorrecto -> "No coincide").
"""

import re

import pytest
from fastapi.testclient import TestClient

from app import db, ledger
from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _pick(conn) -> None:
    ledger.append_pick(conn, {
        "match_id": "m-manual-1", "sport_key": "basketball_nba",
        "sport": "basketball", "league": "NBA · USA", "league_raw": "NBA · USA",
        "event": "Lakers vs Celtics", "market_type": "h2h",
        "selection": "away", "selection_label": "Victoria de Celtics",
        "bookmaker": "Pinnacle", "odds": 1.85, "model_prob": 0.58,
        "market_prob": 0.54, "edge": 0.042, "kelly": {"stake_pct": 1.5},
        "commence_time": "2026-12-01T20:00:00Z",
        "home_team": "Lakers", "away_team": "Celtics",
    })


def test_verify_page_serves_manual_field(client):
    conn = db.connect()
    try:
        _pick(conn)
    finally:
        conn.close()
    html = client.get("/verify/1").text
    assert 'id="manual-hash-input"' in html
    assert 'id="btn-manual-verify"' in html
    assert 'id="manual-verify-box"' in html


def test_pick_js_has_manual_logic_and_i18n(client):
    js = client.get("/pick.js").text
    # Función de comparación y bindeo.
    assert "async function verifyManualHash()" in js
    assert 'addEventListener("click", verifyManualHash)' in js
    # Cadenas ES/EN: el caso negativo debe decir "No coincide".
    assert 'manual_bad: "✗ No coincide' in js
    assert 'manual_bad: "✗ Does not match' in js
    assert 'manual_ok: "✓ Coincide' in js
    # Solo hex de 64 caracteres pasan el formato.
    assert "/^[0-9a-f]{64}$/" in js


def test_manual_hash_compares_against_registered_hash(client):
    """La comparación usa el hash registrado del pick, no el pegado."""
    js = client.get("/pick.js").text
    m = re.search(r"async function verifyManualHash\(\) \{(.*?)\n\}", js, re.S)
    assert m, "verifyManualHash no encontrada"
    body = m.group(1)
    # Orden: validación de formato -> recálculo del canónico -> comparación.
    pos_format = body.index("/^[0-9a-f]{64}$/")
    pos_registered = body.index("p.verification_hash")
    pos_compare = body.index("pasted === String(p.verification_hash)")
    assert pos_format < pos_registered < pos_compare
    # Nunca acepta sin comparar contra el registro.
    assert "pasted === computed" not in body


def test_verify_report_accepts_manual_scope(client):
    r = client.post("/api/verify/report",
                    json={"ok": False, "scope": "manual"})
    assert r.status_code == 200, r.text
    assert client.get("/api/health").json()["verificaciones_hash"] == 1
