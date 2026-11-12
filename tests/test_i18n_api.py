"""La API devuelve textos en inglés cuando se pide ?lang=en."""

import re

from fastapi.testclient import TestClient

from app import providers, service
from app.main import app

# Palabras y frases típicas del español que no deben aparecer en la versión EN.
SPANISH_HINTS = re.compile(
    r"\b(Usamos|cuota|implica|antes de|confianza|mercado|casas|Carrera|"
    r"favorito|marcador|localía|de probabilidad|partidos|Riesgo)\b")


def _all_text(obj) -> str:
    if isinstance(obj, dict):
        return " ".join(_all_text(v) for v in obj.values())
    if isinstance(obj, list):
        return " ".join(_all_text(v) for v in obj)
    return str(obj) if isinstance(obj, str) else ""


def test_english_recommendations_have_no_spanish_explanations():
    matches, src = providers.get_matches()
    res = service.build_recommendations(plan="premium", matches=matches,
                                        source=src, lang="en")
    assert res["picks"]
    for p in res["picks"]:
        text = _all_text(p["explanation"])
        assert not SPANISH_HINTS.search(text), text[:200]
        assert p["explanation"]["steps"][0]["title"].startswith("1. Our model")


def test_english_matches_translate_leagues():
    with TestClient(app) as c:
        body = c.get("/api/matches?lang=en").json()
        leagues = {m["league"] for m in body["matches"]}
        assert "NBA · USA" in leagues or "NHL · USA" in leagues
        assert not any("EE.UU" in l or "Estados Unidos" in l for l in leagues)


def test_spanish_is_still_the_default():
    with TestClient(app) as c:
        body = c.get("/api/recommendations?plan=premium").json()
        if body["picks"]:
            assert body["picks"][0]["explanation"]["steps"][0]["title"].startswith("1. Nuestro modelo")
