"""El registro público es append-only y verificable: estas pruebas lo exigen."""

import time

import pytest

from app import db, ledger, providers, service


def _conn():
    return db.connect()


def _after_event() -> float:
    """Momento posterior al inicio de los eventos de prueba."""
    return ledger._iso_ts("2026-12-02T00:00:00Z")


def _pick(**overrides):
    base = {
        "match_id": "evt-1", "sport": "soccer", "league": "Test League",
        "home_team": "Local", "away_team": "Visitante",
        "selection": "home", "selection_label": "Victoria de Local",
        "bookmaker": "book", "odds": 2.0, "model_prob": 0.55,
        "market_prob": 0.50, "edge": 0.05, "market_type": "h2h",
        "commence_time": "2026-12-01T20:00:00Z",
        "kelly": {"stake_pct": 2.0},
    }
    base.update(overrides)
    return base


def test_append_and_verify_chain():
    conn = _conn()
    try:
        assert ledger.append_pick(conn, _pick())
        assert ledger.append_pick(conn, _pick(match_id="evt-2"))
        report = ledger.verify(conn)
        assert report["ok"] is True
        assert report["chains"]["picks"]["rows"] == 2
    finally:
        conn.close()


def test_editing_a_published_pick_breaks_the_chain():
    conn = _conn()
    try:
        ledger.append_pick(conn, _pick())
        conn.execute("UPDATE picks SET edge = 0.99 WHERE pick_key = 'evt-1'")
        conn.commit()
        report = ledger.verify(conn)
        assert report["ok"] is False
        assert report["chains"]["picks"]["ok"] is False
        assert "editada" in report["chains"]["picks"]["reason"]
    finally:
        conn.close()


def test_deleting_a_published_pick_breaks_the_chain():
    conn = _conn()
    try:
        ledger.append_pick(conn, _pick(match_id="evt-a"))
        ledger.append_pick(conn, _pick(match_id="evt-b"))
        conn.execute("DELETE FROM picks WHERE pick_key = 'evt-a'")
        conn.commit()
        assert ledger.verify(conn)["ok"] is False
    finally:
        conn.close()


def test_one_pick_per_event_is_idempotent():
    conn = _conn()
    try:
        assert ledger.append_pick(conn, _pick()) is True
        assert ledger.append_pick(conn, _pick(selection="away")) is False
        assert db.ledger_counts(conn)["picks_count"] == 1
    finally:
        conn.close()


def test_publish_never_stores_non_live_data():
    conn = _conn()
    try:
        matches, _src = providers.get_matches()
        assert ledger.publish(conn, matches, "sample") == 0
        assert db.ledger_counts(conn)["picks_count"] == 0
    finally:
        conn.close()


def test_publish_stores_every_value_pick_once():
    conn = _conn()
    try:
        matches, _src = providers.get_matches()
        added = ledger.publish(conn, matches, "live")
        again = ledger.publish(conn, matches, "live")
        assert added >= 1
        assert again == 0  # mismo parte: nada nuevo que publicar
        rows, total = db.ledger_pick_rows(conn)
        assert total == added
        assert all(r["source"] == "live" for r in rows)
        assert len({r["event_id"] for r in rows}) == total  # uno por evento
    finally:
        conn.close()


def test_clv_formula_and_capture():
    conn = _conn()
    try:
        assert ledger.clv_pct(2.10, 2.00) == pytest.approx(5.0)
        assert ledger.clv_pct(2.00, 2.10) == pytest.approx(-4.7619, abs=1e-3)
        ledger.append_pick(conn, _pick(), created_at=time.time() - 3600)
        match = {"id": "evt-1", "bookmakers": [
            {"key": "a", "odds": {"home": 1.95, "away": 4.0}},
            {"key": "b", "odds": {"home": 2.00, "away": 3.9}}]}
        adds = ledger.capture_closings(
            conn, [match], now=ledger._iso_ts("2026-12-01T20:00:00Z") - 60,
            window=900)
        assert adds == 1
        row = db.ledger_rows(conn, "pick_closings")[0]
        assert row["closing_odds"] == 2.00
        assert row["clv_pct"] == pytest.approx(0.0)
    finally:
        conn.close()


def test_settle_uses_real_scores_and_never_guesses():
    conn = _conn()
    try:
        ledger.append_pick(conn, _pick(match_id="w"), created_at=time.time())
        ledger.append_pick(conn, _pick(match_id="l"), created_at=time.time())
        scores = {"w": {"home": 2, "away": 0, "completed": True},
                  "l": {"home": 0, "away": 3, "completed": True},
                  "x": {"home": 1, "away": 1, "completed": False}}
        added = ledger.settle(conn, scores, now=_after_event())
        assert added == 2
        results = {r["pick_id"]: r for r in db.ledger_rows(conn, "pick_results")}
        assert sorted(r["result"] for r in results.values()) == ["lost", "won"]
        won = next(r for r in results.values() if r["result"] == "won")
        assert won["profit_units"] == pytest.approx(2.0)  # 2.0u a cuota 2.0
    finally:
        conn.close()


def test_outcome_table():
    assert ledger.outcome_for("home", 2, 1) == "won"
    assert ledger.outcome_for("away", 2, 1) == "lost"
    assert ledger.outcome_for("draw", 1, 1, "soccer") == "won"
    assert ledger.outcome_for("home", 1, 1, "soccer") == "lost"
    assert ledger.outcome_for("home", 1, 1, "basketball") == "push"
    assert ledger.outcome_for("somebody", 1, 0) is None


def test_summary_counts_only_settled_picks():
    conn = _conn()
    try:
        ledger.append_pick(conn, _pick(match_id="a"), created_at=time.time())
        ledger.append_pick(conn, _pick(match_id="b"), created_at=time.time())
        ledger.append_pick(conn, _pick(match_id="c"), created_at=time.time())
        ledger.settle(conn, {"a": {"home": 2, "away": 0, "completed": True},
                             "b": {"home": 0, "away": 1, "completed": True}},
                      now=_after_event())
        s = ledger.summary(conn)
        assert s["sample"] == 2 and s["picks_total"] == 3 and s["pending"] == 1
        assert s["wins"] == 1 and s["losses"] == 1
        assert s["roi_pct"] == pytest.approx(0.0)  # +2.0 y -2.0 sobre 4.0
        assert "muestra" in s["pending_note"].lower()
    finally:
        conn.close()


def test_anchor_summarizes_the_three_chains():
    conn = _conn()
    try:
        ledger.append_pick(conn, _pick())
        a = ledger.anchor(conn, day="2026-11-13")
        b = ledger.anchor(conn, day="2026-11-13", save=False)
        assert a["head_hash"] == b["head_hash"]  # determinista
        assert len(a["head_hash"]) == 64
        assert db.ledger_anchor_on(conn, "2026-11-13")["head_hash"] == a["head_hash"]
        ledger.append_pick(conn, _pick(match_id="evt-2"))
        c = ledger.anchor(conn, day="2026-11-14", save=False)
        assert c["head_hash"] != a["head_hash"]
    finally:
        conn.close()


# ------------------------------------------------------------------- API
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_summary_endpoint_starts_honestly_empty(client):
    body = client.get("/api/ledger/summary").json()
    assert body["sample"] == 0 and body["picks_total"] == 0
    assert body["roi_pct"] == 0.0
    assert body["model_version"]


def test_picks_endpoint_and_csv_include_hashes(client):
    conn = _conn()
    try:
        ledger.append_pick(conn, _pick())
        ledger.append_pick(conn, _pick(match_id="evt-2"))
    finally:
        conn.close()

    body = client.get("/api/ledger/picks").json()
    assert body["total"] == 2
    latest = body["picks"][0]
    genesis = body["picks"][1]
    assert latest["result"] == "pending"
    assert latest["edge_pct"] == pytest.approx(5.0)
    assert len(latest["row_hash"]) == 64
    assert genesis["prev_hash"] == ""  # primera fila de la cadena
    assert latest["prev_hash"] == genesis["row_hash"]  # encadenadas

    csv_resp = client.get("/api/ledger/picks?format=csv")
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers["content-type"]
    assert "attachment" in csv_resp.headers["content-disposition"]
    text = csv_resp.text
    assert "row_hash" in text and "prev_hash" in text
    assert "Victoria de Local" in text


def test_pending_filter_and_verify_endpoint(client):
    conn = _conn()
    try:
        ledger.append_pick(conn, _pick())
        ledger.settle(conn, {"evt-1": {"home": 2, "away": 0, "completed": True}},
                      now=_after_event())
    finally:
        conn.close()
    assert client.get("/api/ledger/picks?result=won").json()["total"] == 1
    assert client.get("/api/ledger/picks?result=lost").json()["total"] == 0
    verify = client.get("/api/ledger/verify").json()
    assert verify["ok"] is True
    assert verify["chains"]["picks"]["rows"] == 1


def test_cycle_publishes_closes_settles_and_anchors():
    matches, _src = providers.get_matches()
    starts = [ledger._iso_ts(m.get("commence_time")) for m in matches]
    first = min(s for s in starts if s)

    def provider():
        return matches, "live"

    r1 = ledger.cycle(provider, now=first - 3600,
                      scores_fetcher=lambda _k: {})
    assert r1["published"] >= 1 and r1["source"] == "live"

    conn = _conn()
    try:
        published = db.ledger_rows(conn, "picks")
        # Marcador que da por ganada la selección publicada de cada evento.
        scores = {}
        for p in published:
            if p["selection"] == "away":
                scores[str(p["event_id"])] = {"home": 0, "away": 2,
                                              "completed": True}
            elif p["selection"] == "draw":
                scores[str(p["event_id"])] = {"home": 1, "away": 1,
                                              "completed": True}
            else:
                scores[str(p["event_id"])] = {"home": 2, "away": 0,
                                              "completed": True}
        assert db.ledger_anchor_on(conn, time.strftime(
            "%Y-%m-%d", time.gmtime(first - 3600))) is not None
    finally:
        conn.close()

    r2 = ledger.cycle(provider, now=first - 60,
                      scores_fetcher=lambda _k: scores)
    assert r2["closings"] >= 1 and r2["settled"] == 0

    r3 = ledger.cycle(provider, now=first + 3600,
                      scores_fetcher=lambda _k: scores)
    assert r3["settled"] >= 1

    conn = _conn()
    try:
        s = ledger.summary(conn)
        assert s["sample"] >= 1 and s["picks_total"] >= s["sample"]
        assert s["losses"] == 0  # todos los marcadores de prueba: gana local
    finally:
        conn.close()


def test_by_league_labels_small_samples_as_not_significant():
    conn = _conn()
    try:
        ledger.append_pick(conn, _pick())
        ledger.settle(conn, {"evt-1": {"home": 2, "away": 0, "completed": True}},
                      now=_after_event())
        data = ledger.by_league(conn)
        data.pop("_total_picks")
        card = data["Test League"]
        assert card["picks"] == 1 and card["sample"] == 1
        assert card["significant"] is False  # n < 30: no se declara nada
    finally:
        conn.close()
