"""Tests del pipeline de recomendaciones y de la API."""

import pytest
from fastapi.testclient import TestClient

from app import providers, service
from app.main import app


@pytest.fixture(scope="module")
def matches():
    m, src = providers.get_matches()
    assert src == "sample" and len(m) >= 5
    return m


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ------------------------------------------------------------- servicio
def test_every_pick_has_positive_expected_value(matches):
    result = service.build_recommendations(plan="premium", matches=matches,
                                           source="sample")
    assert result["count"] > 0
    for p in result["picks"]:
        assert p["ev"] > 0, "solo se recomienda con EV > 0"
        assert p["edge"] >= result["min_edge"]
        assert p["odds"] > 1.0
        assert 0.0 <= p["confidence"] <= 1.0
        assert p["kelly"]["stake_pct"] <= 3.0  # tope duro de riesgo


def test_free_plan_is_more_restrictive_than_premium(matches):
    free = service.build_recommendations(plan="free", matches=matches, source="sample")
    prem = service.build_recommendations(plan="premium", matches=matches, source="sample")
    assert free["count"] <= prem["count"]
    assert free["count"] <= 10  # plan Free: 10 recomendaciones diarias
    assert free["min_edge"] >= prem["min_edge"]
    for p in free["picks"]:
        assert p["edge"] >= 0.06
        # Free: solo modelo, mercado y valor; el resto está bloqueado.
        assert len(p["explanation"]["steps"]) == 3
        assert p["explanation"].get("locked_note")
        assert "backtest" not in p


def test_one_pick_per_match_and_ranked(matches):
    prem = service.build_recommendations(plan="premium", matches=matches, source="sample")
    ids = [p["match_id"] for p in prem["picks"]]
    assert len(ids) == len(set(ids))
    # Ranking: puntuación = edge × (0.5 + 0.5·confianza), descendente.
    scores = [p["score"] for p in prem["picks"]]
    assert scores == sorted(scores, reverse=True)


def test_explanation_is_complete(matches):
    prem = service.build_recommendations(plan="premium", matches=matches, source="sample")
    exp = prem["picks"][0]["explanation"]
    assert exp["summary"]
    assert len(exp["steps"]) == 6
    assert exp["risks"]
    titles = " ".join(s["title"] for s in exp["steps"])
    for word in ("modelo", "mercado", "Kelly", "confiar"):
        assert word.lower() in titles.lower()
    # El backtest respalda la afirmación de confianza.
    assert prem["picks"][0]["backtest"]["bets"] > 0


def test_soccer_model_probabilities_sum_to_one(matches):
    for m in matches:
        probs, _meta = service.predict(m)
        assert sum(probs.values()) == pytest.approx(1.0, abs=1e-6)


def test_matches_overview(matches):
    overview = service.matches_overview(matches)
    assert len(overview) == len(matches)
    for o in overview:
        assert set(o["model_probabilities"]) == set(o["market_probabilities"]) or \
            set(o["model_probabilities"]).issuperset(o["market_probabilities"])
        assert o["books"] >= 1


# ---------------------------------------------------------------- API
def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["source"] == "sample"


def test_recommendations_endpoint(client):
    r = client.get("/api/recommendations?plan=premium")
    assert r.status_code == 200
    body = r.json()
    assert body["plan"] == "premium"
    assert body["picks"]
    assert body["picks"][0]["explanation"]["steps"]


def test_recommendations_validates_params(client):
    assert client.get("/api/recommendations?plan=gold").status_code == 422
    assert client.get("/api/recommendations?bankroll=-5").status_code == 422


def test_matches_endpoint(client):
    r = client.get("/api/matches?sport=soccer")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 1
    assert all(m["sport"] == "soccer" for m in body["matches"])


def test_performance_endpoint(client):
    r = client.get("/api/performance")
    assert r.status_code == 200
    body = r.json()
    assert body["bets"] > 0
    assert "roi_pct" in body and "binomial_p_value" in body
    r2 = client.get("/api/performance/by-sport")
    assert r2.status_code == 200
    assert "soccer" in r2.json()["by_sport"]


def test_methodology_and_plans(client):
    m = client.get("/api/methodology").json()
    assert len(m["pipeline"]) >= 8
    assert m["honest_limits"]  # nunca promete "sin fallas"
    p = client.get("/api/plans").json()
    assert set(p["plans"]) == {"free", "premium"}


def test_subscribe(client):
    ok = client.post("/api/subscribe", json={"email": "apostador@test.com",
                                             "plan": "free"})
    assert ok.status_code == 200
    bad = client.post("/api/subscribe", json={"email": "no-es-correo", "plan": "premium"})
    assert bad.status_code == 400


def test_frontend_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "ApuestaEdge" in r.text
