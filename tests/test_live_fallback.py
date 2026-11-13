"""Datos en vivo: cero eventos inventados y respaldo con el último parte.

Reglas que protegen la credibilidad del radar:

1. Con ``ODDS_API_KEY`` configurada la página NUNCA muestra el dataset de
   demostración: o hay datos reales, el último parte real guardado, o se
   indica "sin datos" (``unavailable``).
2. Cada fetch exitoso se persiste en ``kv`` y sirve de respaldo cuando la
   API falla (cuota agotada, red caída), descartando eventos ya iniciados.
3. Los deportes outright (F1/MotoGP/caballos) no tienen fuente real y se
   mantienen fuera del radar aunque aparezcan en los datos.
"""

from __future__ import annotations

import json
import time

import pytest

from app import config, db, main, providers


def _reset_cache() -> None:
    main._CACHE.update(ts=0.0, matches=None, source=None, updated_at=0.0)


@pytest.fixture(autouse=True)
def clean_cache():
    """El caché de partidos es global: se limpia antes y después de cada test."""
    _reset_cache()
    yield
    _reset_cache()


def _future_event(event_id: str = "live-1", sport_group: str = "soccer",
                  hours_ahead: float = 2.0) -> dict:
    start = time.time() + hours_ahead * 3600
    return {
        "id": event_id,
        "sport_group": sport_group,
        "sport_key": "soccer_epl",
        "league": "EPL",
        "commence_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(start)),
        "home_team": "Team A",
        "away_team": "Team B",
        "bookmakers": [{"key": "demo", "title": "Demo",
                        "odds": {"home": 2.0, "draw": 3.4, "away": 3.6}}],
    }


def _configure_live(monkeypatch, fetch) -> None:
    monkeypatch.setattr(config, "ODDS_API_KEY", "test-key")
    monkeypatch.setattr(config, "ALLOW_SAMPLE_DATA", False)
    monkeypatch.setattr(providers, "get_matches", fetch)
    _reset_cache()


def test_no_sample_when_api_fails_and_key_is_set(monkeypatch):
    """Con clave configurada, un fallo de la API no muestra la demo."""
    _configure_live(monkeypatch, lambda: (None, "error"))
    matches, source = main._get_matches()
    assert source == "unavailable"
    assert matches == []


def test_snapshot_is_used_when_api_fails(monkeypatch):
    """El último parte real guardado se muestra si la API falla."""
    db.kv_set(main._SNAPSHOT_KEY, json.dumps(
        {"ts": time.time(), "matches": [_future_event()]}))
    _configure_live(monkeypatch, lambda: (None, "error"))
    matches, source = main._get_matches()
    assert source == "live_cached"
    assert [m["id"] for m in matches] == ["live-1"]


def test_snapshot_drops_events_already_started(monkeypatch):
    """Un parte con eventos iniciados no se muestra (fechas viejas)."""
    db.kv_set(main._SNAPSHOT_KEY, json.dumps(
        {"ts": time.time(),
         "matches": [_future_event("old-1", hours_ahead=-5.0)]}))
    _configure_live(monkeypatch, lambda: (None, "error"))
    matches, source = main._get_matches()
    assert source == "unavailable"
    assert matches == []


def test_expired_snapshot_is_ignored(monkeypatch):
    """Un parte de más de 7 días no se muestra como si fuera actual."""
    db.kv_set(main._SNAPSHOT_KEY, json.dumps(
        {"ts": time.time() - 8 * 24 * 3600,
         "matches": [_future_event("ancient", hours_ahead=100.0)]}))
    _configure_live(monkeypatch, lambda: (None, "error"))
    _matches, source = main._get_matches()
    assert source == "unavailable"


def test_successful_live_fetch_is_persisted(monkeypatch):
    """Cada fetch en vivo se guarda como respaldo en la BD."""
    _configure_live(monkeypatch, lambda: ([_future_event()], "live"))
    matches, source = main._get_matches()
    assert source == "live" and len(matches) == 1
    stored = db.kv_get(main._SNAPSHOT_KEY)
    assert stored is not None
    assert "live-1" in stored[0]


def test_outright_sports_never_reach_the_radar(monkeypatch):
    """F1/MotoGP/caballos (sin fuente real) siguen ocultos en vivo."""
    events = [_future_event("race-1", sport_group="formula1"),
              _future_event("game-1", sport_group="basketball")]
    _configure_live(monkeypatch, lambda: (events, "live"))
    matches, _source = main._get_matches()
    assert [m["id"] for m in matches] == ["game-1"]


def test_plan_keys_skips_offseason_and_discovers_tennis():
    """Solo se piden deportes en temporada; el tenis se descubre."""
    in_season = {"soccer_epl", "basketball_nba", "icehockey_nhl",
                 "tennis_atp_finals", "tennis_wta_finals"}
    plan = dict(providers.plan_keys(in_season))
    assert plan["soccer"] == ["soccer_epl"]
    assert plan["basketball"] == ["basketball_nba"]
    assert plan["hockey"] == ["icehockey_nhl"]
    # Sin temporada -> sin peticiones de boxeo/NFL/NCAA (ahorro de cuota).
    assert "boxing" not in plan and "americanfootball" not in plan
    # Torneos de tenis en temporada, con la clave correcta (doble n).
    assert plan["tennis"] == ["tennis_atp_finals", "tennis_wta_finals"]
    # Sin descubrimiento (lista vacía) se usan las claves configuradas.
    fallback = dict(providers.plan_keys(set()))
    assert "americanfootball_ncaaf" in fallback["americanfootball"]
