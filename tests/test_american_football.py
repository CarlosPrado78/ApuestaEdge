"""Tests del fútbol americano (NFL/NCAA) como cuarto deporte soportado."""

from app import providers, service
from app.explain import MODEL_LABELS, SPORT_LABELS


def test_sport_group_recognizes_american_football():
    assert providers._sport_group("americanfootball_nfl") == "americanfootball"
    assert providers._sport_group("americanfootball_ncaa_fbs") == "americanfootball"
    # Los demás siguen intactos.
    assert providers._sport_group("soccer_epl") == "soccer"
    assert providers._sport_group("basketball_nba") == "basketball"
    assert providers._sport_group("tennis_atp") == "tennis"


def test_selections_are_moneyline_without_draw():
    # La NFL no tiene empate en el mercado h2h: solo local/visitante.
    assert providers.SELECTIONS["americanfootball"] == ["home", "away"]


def test_config_includes_nfl_and_ncaa():
    from app import config
    keys = config.ODDS_API_SPORTS["americanfootball"]
    assert "americanfootball_nfl" in keys
    assert "americanfootball_ncaa_fbs" in keys


def test_sample_data_has_nfl_matches():
    matches, src = providers.load_sample_matches(), "sample"
    nfl = [m for m in matches if m["sport_group"] == "americanfootball"]
    assert len(nfl) >= 3
    for m in nfl:
        assert m["home_team"] and m["away_team"]
        assert m["elo_home"] > 0 and m["elo_away"] > 0  # ratings cargados
        assert len(m["bookmakers"]) >= 2


def test_nfl_probabilities_are_a_valid_moneyline():
    matches, _ = providers.get_matches()
    nfl = [m for m in matches if m["sport_group"] == "americanfootball"]
    assert nfl
    for m in nfl:
        probs, meta = service.predict(m)
        assert set(probs) == {"home", "away"}
        assert abs(sum(probs.values()) - 1.0) < 1e-9
        assert 0.0 < probs["home"] < 1.0
        assert meta["model"] == MODEL_LABELS["americanfootball"]


def test_nfl_home_advantage_is_applied():
    # Con ratings iguales, el local debe ser favorito (localía > 0).
    m = {"sport_group": "americanfootball", "home_team": "A", "away_team": "B",
         "elo_home": 1600.0, "elo_away": 1600.0}
    probs, _ = service.predict(m)
    assert probs["home"] > 0.5


def test_nfl_recommendations_include_value(matches=None):
    matches, src = providers.get_matches()
    res = service.build_recommendations(plan="premium", matches=matches,
                                        source=src)
    nfl_picks = [p for p in res["picks"] if p["sport"] == "americanfootball"]
    # La demo NFL está calibrada para producir picks con valor.
    assert nfl_picks, "la demo debe generar al menos un pick NFL con valor"
    for p in nfl_picks:
        assert p["ev"] > 0 and p["edge"] >= res["min_edge"]
        assert p["kelly"]["stake_pct"] <= 3.0
        assert SPORT_LABELS["americanfootball"] in p["explanation"]["summary"] \
            or "Chiefs" in p["explanation"]["summary"] \
            or "NFL" in p["league"]


def test_sport_filter_works_for_american_football():
    matches, src = providers.get_matches()
    res = service.build_recommendations(plan="premium", sport="americanfootball",
                                        matches=matches, source=src)
    assert res["models_scanned"] >= 3
    assert all(p["sport"] == "americanfootball" for p in res["picks"])


def test_labels_are_spanish():
    assert SPORT_LABELS["americanfootball"] == "Fútbol americano"
    assert "moneyline" in MODEL_LABELS["americanfootball"]
