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


# --------------------------------------------------- paquete de verificación
def _seed_three_chains(conn):
    pick = _pick()
    ledger.append_pick(conn, pick)
    row = db.ledger_rows(conn, "picks")[0]
    ledger.append("pick_closings", conn, {
        "pick_id": int(row["id"]), "closing_odds": 1.95,
        "closing_at": _after_event(), "clv_pct": ledger.clv_pct(2.0, 1.95)})
    ledger.append("pick_results", conn, {
        "pick_id": int(row["id"]), "result": "won",
        "profit_units": 1.0, "settled_at": _after_event()})
    return conn


def test_export_package_is_verifiable_by_the_standalone_script(tmp_path):
    import json
    import subprocess
    import sys

    from app import config

    conn = _conn()
    try:
        _seed_three_chains(conn)
        package = ledger.export_package(conn)
    finally:
        conn.close()

    assert package["server_check"]["ok"] is True
    assert set(package["tables"]) == {"picks", "pick_closings", "pick_results"}
    for table, rows in package["tables"].items():
        assert rows and all(r.get("canonical") for r in rows)
        spec = package["algorithm"]["tables"][table]
        assert set(spec["fields"]) <= set(rows[0])
        assert spec["ints"] == (["pick_id"] if table != "picks" else [])

    path = tmp_path / "ledger.json"
    path.write_text(json.dumps(package), encoding="utf-8")
    script = config.BASE_DIR / "static" / "verify_ledger.py"
    ok = subprocess.run([sys.executable, str(script), str(path)],
                        capture_output=True, text=True)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert "registro íntegro" in ok.stdout

    # Una fila editada en el paquete debe hacer fallar al verificador.
    package["tables"]["picks"][0]["bet_odds"] = 9.99
    tampered = tmp_path / "ledger_tampered.json"
    tampered.write_text(json.dumps(package), encoding="utf-8")
    bad = subprocess.run([sys.executable, str(script), str(tampered)],
                         capture_output=True, text=True)
    assert bad.returncode == 1
    assert "NO cuadra" in bad.stdout


def test_verification_page_and_package_endpoint(client):
    conn = _conn()
    try:
        _seed_three_chains(conn)
    finally:
        conn.close()
    page = client.get("/verificacion")
    assert page.status_code == 200
    assert "/verificacion.js" in page.text
    assert "The Odds API" not in page.text
    script = client.get("/verificacion/verify_ledger.py")
    assert script.status_code == 200
    assert "hashlib" in script.text  # se puede leer antes de ejecutarlo
    package = client.get("/api/ledger/export").json()
    assert package["server_check"]["ok"] is True
    assert len(package["tables"]["picks"]) == 1


# --------------------------------------------------- ligas y modelo
def test_leagues_endpoint_separates_small_samples(client):
    conn = _conn()
    try:
        for i in range(2):
            ledger.append_pick(conn, _pick(match_id=f"lg-{i}",
                                           league="Liga Pequeña"))
    finally:
        conn.close()
    body = client.get("/api/ledger/leagues").json()
    league = body["leagues"]["Liga Pequeña"]
    assert league["sample"] == 0
    assert league["significant"] is False
    assert body["total_picks"] == 2


def test_league_page_and_model_page_are_public(client):
    for path in ("/ligas", "/modelo"):
        page = client.get(path)
        assert page.status_code == 200
        assert 'class="nav"' in page.text
        assert "The Odds API" not in page.text
        assert "ODDS_API_KEY" not in page.text
    assert "/ligas.js" in client.get("/ligas").text
    assert "/modelo.js" in client.get("/modelo").text


def test_model_page_explains_the_auditable_logic(client):
    page = client.get("/modelo").text
    assert "Kelly" in page and "CLV" in page and "binomial" in page.lower()
    versions = client.get("/api/ledger/versions").json()
    assert versions["current"]
    assert isinstance(versions["versions"], list)


# ------------------------------------------- archivo: Free 7 días / Premium todo
def test_free_history_is_limited_to_seven_days(client):
    conn = _conn()
    try:
        ledger.append_pick(conn, _pick(
            match_id="old-1", odds=1.91,
            commence_time="2026-10-01T20:00:00Z"))
        ledger.append_pick(conn, _pick(
            match_id="recent-1", odds=2.05,
            commence_time="2026-11-20T20:00:00Z"))
    finally:
        conn.close()

    free = client.get("/api/ledger/picks").json()
    assert free["history_limited"] is True and free["history_days"] == 7
    assert [round(p["bet_odds"], 2) for p in free["picks"]] == [2.05]

    # Un filtro explícito anterior tampoco salta el límite.
    old = client.get("/api/ledger/picks?date_from=2026-09-01").json()
    assert old["total"] == 1
    assert round(old["picks"][0]["bet_odds"], 2) == 2.05

    # Premium ve el archivo completo.
    email = "archivo@test.com"
    client.post("/api/auth/register",
                json={"email": email, "password": "secret123"})
    token = client.post("/api/auth/login",
                        json={"email": email,
                              "password": "secret123"}).json()["token"]
    conn = _conn()
    try:
        db.set_user_plan(conn, email, "premium")
    finally:
        conn.close()
    full = client.get("/api/ledger/picks",
                      headers={"Authorization": f"Bearer {token}"}).json()
    assert full["history_limited"] is False and full["history_days"] is None
    assert full["total"] == 2


# ------------------------------------ P1: permalink, SEO, OTS y versiones
def test_pick_permalink_and_detail_api(client):
    conn = _conn()
    try:
        ledger.append_pick(conn, _pick(match_id="perm-1", odds=2.20),
                           created_at=1000.0)
        ledger.append("pick_closings", conn, {
            "pick_id": 1, "closing_odds": 2.00,
            "closing_at": 1500.0, "clv_pct": 10.0,
        })
        ledger.append("pick_results", conn, {
            "pick_id": 1, "result": "won",
            "profit_units": 1.2, "settled_at": 5000.0,
        })
    finally:
        conn.close()

    detail = client.get("/api/ledger/picks/1")
    assert detail.status_code == 200
    body = detail.json()
    assert body["id"] == 1
    assert body["pick_canonical"] and body["closing_canonical"] and body["result_canonical"]
    assert body["row_hash"] and body["closing_row_hash"] and body["result_row_hash"]

    page = client.get("/pick/1")
    assert page.status_code == 200
    assert 'property="og:title"' in page.text
    assert 'rel="canonical"' in page.text
    assert "application/ld+json" in page.text
    assert "window.__PICK_DATA__" in page.text
    assert body["row_hash"] in page.text
    assert client.get("/pick/99999").status_code == 404


def test_sitemap_xml_and_robots_txt_include_public_pages_and_picks(client):
    conn = _conn()
    try:
        ledger.append_pick(conn, _pick(match_id="seo-1", odds=2.10))
    finally:
        conn.close()

    robots = client.get("/robots.txt")
    assert robots.status_code == 200
    assert "Sitemap:" in robots.text and "/sitemap.xml" in robots.text

    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200
    for path in ("/picks", "/ligas", "/modelo", "/verificacion", "/alertas", "/pick/1"):
        assert f"{path}</loc>" in sitemap.text


def test_anchor_generates_opentimestamps_ots_proof(client):
    conn = _conn()
    try:
        ledger.append_pick(conn, _pick(match_id="ots-1", odds=2.05))
        anc = ledger.anchor(conn, day="2026-11-14", now=2000.0)
        assert anc["ots_proof"].startswith(ledger.OTS_HEADER.hex())

        class _FakeResp:
            status_code = 200
            content = b"\xf0\x04test"

        stamped = ledger.stamp_anchor(
            conn, "2026-11-14", anc["head_hash"],
            calendar_url="https://a.pool.opentimestamps.org",
            http_post=lambda url, digest: _FakeResp(),
            now=2005.0,
        )
        assert stamped["ots_calendar"] == "https://a.pool.opentimestamps.org"
    finally:
        conn.close()

    ots = client.get("/api/ledger/anchors/2026-11-14.ots")
    assert ots.status_code == 200
    assert ots.headers["content-type"].startswith("application/vnd.opentimestamps.v1")
    assert ots.content.startswith(ledger.OTS_HEADER)
    assert ots.content.endswith(b"\xf0\x04test")


def test_versions_endpoint_includes_measured_impact(client):
    conn = _conn()
    try:
        ledger.append_pick(conn, _pick(match_id="imp-1", odds=2.00),
                           created_at=1000.0)
        ledger.append("pick_results", conn, {
            "pick_id": 1, "result": "won",
            "profit_units": 1.0, "settled_at": 3000.0,
        })
    finally:
        conn.close()

    body = client.get("/api/ledger/versions").json()
    current = next(v for v in body["versions"] if v["version"] == body["current"])
    imp = current["measured_impact"]
    assert imp["picks"] == 1
    assert imp["sample"] == 1
    assert imp["wins"] == 1 and imp["losses"] == 0
