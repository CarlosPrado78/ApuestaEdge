"""Tests de boxeo, béisbol, Fórmula 1, MotoGP y carreras de caballos.

Boxeo y béisbol son mercados h2h como el resto; F1, MotoGP y caballos
son mercados outright (ganador de la carrera con N participantes) que usan
Bradley-Terry sobre ratings Elo.
"""

from fastapi.testclient import TestClient

from app import config, providers, service
from app.explain import MODEL_LABELS, SPORT_LABELS

NUEVOS = ["boxing", "baseball", "formula1", "motogp", "horseracing"]
OUTRIGHT = ["formula1", "motogp", "horseracing"]


def test_sport_group_recognizes_new_sports():
    assert providers._sport_group("boxing_boxing") == "boxing"
    assert providers._sport_group("baseball_mlb") == "baseball"
    assert providers._sport_group("formula1_gp") == "formula1"
    assert providers._sport_group("motogp_gp") == "motogp"
    assert providers._sport_group("horseracing_gp") == "horseracing"
    # Los anteriores siguen intactos.
    assert providers._sport_group("soccer_epl") == "soccer"
    assert providers._sport_group("americanfootball_nfl") == "americanfootball"


def test_config_live_keys_and_demo_only_outright():
    # Boxeo y béisbol: cobertura en vivo en The Odds API.
    assert "boxing_boxing" in config.ODDS_API_SPORTS["boxing"]
    assert "baseball_mlb" in config.ODDS_API_SPORTS["baseball"]
    # Outright: sin proveedor en vivo -> solo demo, etiquetado como tal.
    for g in OUTRIGHT:
        assert config.ODDS_API_SPORTS[g] == []
        assert g in config.DEMO_ONLY_SPORTS
        assert g in config.OUTRIGHT_GROUPS


def test_h2h_new_sports_use_moneyline_selections():
    assert providers.SELECTIONS["boxing"] == ["home", "away"]
    assert providers.SELECTIONS["baseball"] == ["home", "away"]


def test_sample_covers_every_new_sport():
    matches = providers.load_sample_matches()
    for g in NUEVOS:
        assert any(m["sport_group"] == g for m in matches), \
            f"faltan datos demo de {g}"


def test_outright_events_have_participants_and_ratings():
    for m in providers.load_sample_matches():
        if m["sport_group"] not in OUTRIGHT:
            continue
        parts = m.get("participants")
        assert parts and len(parts) >= 6
        elo = m.get("elo_participants")
        assert elo and set(elo) == set(parts)
        assert all(v > 0 for v in elo.values())
        # Cada casa ofrece cuota por cada participante (mercado outright).
        for bm in m["bookmakers"]:
            assert set(bm["odds"]) == set(parts)
            assert all(o > 1.0 for o in bm["odds"].values())


def test_outright_probabilities_are_a_valid_distribution():
    for m in providers.load_sample_matches():
        if m["sport_group"] not in OUTRIGHT:
            continue
        probs, meta = service.predict(m)
        assert set(probs) == set(m["participants"])
        assert abs(sum(probs.values()) - 1.0) < 1e-9
        assert all(0.0 < p < 1.0 for p in probs.values())
        assert meta["field_size"] == len(m["participants"])
        assert meta["model"] == MODEL_LABELS[m["sport_group"]]


def test_bradley_terry_equals_elo_logistic_for_two():
    # Coherencia: con N=2, Bradley-Terry coincide con la logística Elo.
    m = {"sport_group": "formula1", "home_team": "A", "away_team": "B",
         "participants": ["A", "B"],
         "elo_participants": {"A": 1900.0, "B": 1840.0}}
    probs, _ = service.predict(m)
    p_log = 1.0 / (1.0 + 10 ** ((1840.0 - 1900.0) / 400.0))
    assert abs(probs["A"] - p_log) < 1e-12
    assert abs(sum(probs.values()) - 1.0) < 1e-12


def test_h2h_new_sports_probabilities():
    matches, _ = providers.get_matches()
    for g in ("boxing", "baseball"):
        for m in [x for x in matches if x["sport_group"] == g]:
            probs, _ = service.predict(m)
            assert set(probs) == {"home", "away"}
            assert abs(sum(probs.values()) - 1.0) < 1e-9
            assert 0.0 < probs["home"] < 1.0


def test_boxing_has_no_home_advantage():
    # Terreno neutral: ratings iguales -> 50/50.
    m = {"sport_group": "boxing", "home_team": "A", "away_team": "B",
         "elo_home": 1800.0, "elo_away": 1800.0}
    probs, _ = service.predict(m)
    assert abs(probs["home"] - 0.5) < 1e-12


def test_baseball_home_advantage_at_equal_ratings():
    m = {"sport_group": "baseball", "home_team": "A", "away_team": "B",
         "elo_home": 1600.0, "elo_away": 1600.0}
    probs, _ = service.predict(m)
    assert probs["home"] > 0.5  # la localía MLB inclina el partido


def test_recommendations_include_new_sports():
    matches, src = providers.get_matches()
    res = service.build_recommendations(plan="premium", matches=matches,
                                        source=src)
    by_sport = {p["sport"] for p in res["picks"]}
    assert {"boxing", "baseball"} <= by_sport
    assert by_sport & set(OUTRIGHT), "debe haber picks outright en el radar"
    for p in res["picks"]:
        if p["sport"] in NUEVOS:
            assert p["ev"] > 0 and p["edge"] >= res["min_edge"]
            assert p["kelly"]["stake_pct"] <= 3.0
            assert 0.0 <= p["confidence"] <= 1.0


def test_outright_pick_explanation_is_specific():
    matches, src = providers.get_matches()
    res = service.build_recommendations(plan="premium", matches=matches,
                                        source=src)
    p = next(x for x in res["picks"] if x["market_type"] == "outright")
    exp = p["explanation"]
    assert "Bradley-Terry" in exp["steps"][0]["detail"]
    assert str(p["field_size"]) in exp["steps"][0]["detail"]
    assert any("multi-participante" in r for r in exp["risks"])
    assert p["elo_selection"] > 0


def test_boxing_explanation_mentions_neutral_venue():
    matches, src = providers.get_matches()
    res = service.build_recommendations(plan="premium", sport="boxing",
                                        matches=matches, source=src)
    assert res["picks"]
    step = res["picks"][0]["explanation"]["steps"][0]["detail"]
    assert "sin localía" in step
    assert "localía" not in step.replace("sin localía", "")


def test_sport_filters_via_api_for_new_sports():
    from app.main import app
    with TestClient(app) as client:
        # Con cobertura real: boxeo y béisbol visibles.
        for g in ("boxing", "baseball"):
            body = client.get(f"/api/matches?sport={g}").json()
            assert body["count"] >= 1, g
            assert all(m["sport"] == g for m in body["matches"])
        # Ocultos temporalmente (sin datos reales): no aparecen en la API.
        for g in OUTRIGHT:
            body = client.get(f"/api/matches?sport={g}").json()
            assert body["count"] == 0, g


def test_overview_exposes_event_and_field_size():
    matches, _ = providers.get_matches()
    ov = service.matches_overview(matches)
    f1 = next(o for o in ov if o["sport"] == "formula1")
    assert f1["market_type"] == "outright"
    assert f1["event"]
    assert f1["field_size"] == 10
    assert abs(sum(f1["model_probabilities"].values()) - 1.0) < 1e-6


def test_labels_cover_all_new_sports_in_spanish():
    for g in NUEVOS:
        assert g in SPORT_LABELS, g
        assert g in MODEL_LABELS, g
        assert SPORT_LABELS[g][0].isupper()
