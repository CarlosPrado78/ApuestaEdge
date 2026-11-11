"""Proveedores de datos: The Odds API + dataset de demostración.

Flujo:

1. Si existe ``ODDS_API_KEY`` en el entorno, se consultan cuotas en
   vivo (The Odds API, plan gratis).
2. Cualquier fallo o ausencia de clave cae al dataset de demostración
   incluido en ``data/sample_odds.json`` (partidos y cuotas realistas),
   para que la aplicación funcione sin configuración.

Además se normalizan los equipos a ratings Elo desde ``data/ratings.json``.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from . import config

log = logging.getLogger("apuesta_edge.providers")

SELECTIONS = {"soccer": ["home", "draw", "away"],
              "basketball": ["home", "away"],
              "tennis": ["home", "away"],
              "americanfootball": ["home", "away"],
              "boxing": ["home", "away"],
              "baseball": ["home", "away"]}
# Los deportes outright (F1, MotoGP, caballos) no tienen selecciones
# fijas: las ofrece cada evento en ``match["participants"]`.


def _load_json(path) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return None


def load_ratings() -> dict[str, float]:
    """Ratings Elo por equipo (fallback: 1500 = rating inicial)."""
    return _load_json(config.asset_path("ratings.json")) or {}


def load_sample_matches() -> list[dict[str, Any]]:
    data = _load_json(config.SAMPLE_ODDS_PATH) or {}
    matches = data.get("matches", [])
    for m in matches:
        _attach_ratings(m, load_ratings())
    return matches


def _attach_ratings(match: dict, ratings: dict[str, float]) -> None:
    match.setdefault("elo_home", ratings.get(match.get("home_team", ""), 1500.0))
    match.setdefault("elo_away", ratings.get(match.get("away_team", ""), 1500.0))
    # Outright: rating Elo de cada participante de la carrera/combate.
    parts = match.get("participants") or []
    if parts:
        match.setdefault("elo_participants",
                         {p: float(ratings.get(p, 1500.0)) for p in parts})


def _sport_group(sport_key: str) -> str:
    if sport_key.startswith("soccer"):
        return "soccer"
    if sport_key.startswith("basketball"):
        return "basketball"
    if sport_key.startswith("tennis"):
        return "tennis"
    if sport_key.startswith("americanfootball"):
        return "americanfootball"
    if sport_key.startswith("boxing"):
        return "boxing"
    if sport_key.startswith("baseball"):
        return "baseball"
    if sport_key.startswith("formula1"):
        return "formula1"
    if sport_key.startswith("motogp"):
        return "motogp"
    if sport_key.startswith("horseracing"):
        return "horseracing"
    raise ValueError(f"deporte no soportado: {sport_key}")


def _map_h2h_outcomes(outcomes: list[dict], home: str, away: str,
                      group: str) -> dict[str, float]:
    """Convierte los outcomes de la API (nombres de equipo) a home/draw/away."""
    odds: dict[str, float] = {}
    for oc in outcomes:
        name = str(oc.get("name", "")).strip()
        price = float(oc.get("price", 0) or 0)
        if price <= 1.0:
            continue
        lname = name.lower()
        if lname == "draw" or lname == "tie":
            odds["draw"] = price
        elif name == home or lname == home.lower():
            odds["home"] = price
        elif name == away or lname == away.lower():
            odds["away"] = price
        elif group != "soccer":
            # Deportes sin empate: primer outcome = local, segundo = visitante.
            if "home" not in odds:
                odds["home"] = price
            elif "away" not in odds:
                odds["away"] = price
    # Validación mínima: hace falta al menos la selección local.
    if "home" not in odds and group != "soccer":
        if len(outcomes) >= 2:
            odds = {"home": float(outcomes[0]["price"]),
                    "away": float(outcomes[1]["price"])}
    return odds


def fetch_live_matches() -> tuple[list[dict], str]:
    """Obtiene cuotas en vivo. Devuelve ``(matches, fuente)``.

    Si no hay clave o la llamada falla, devuelve la demo y lo indica.
    """
    if not config.ODDS_API_KEY:
        return load_sample_matches(), "sample"
    ratings = load_ratings()
    matches: list[dict] = []
    try:
        with httpx.Client(base_url="https://api.the-odds-api.com/v4",
                          timeout=config.ODDS_API_TIMEOUT) as client:
            for group, keys in config.ODDS_API_SPORTS.items():
                for key in keys:
                    resp = client.get(
                        f"/sports/{key}/odds",
                        params={"apiKey": config.ODDS_API_KEY,
                                "regions": config.ODDS_API_REGION,
                                "markets": "h2h",
                                "oddsFormat": "decimal"})
                    if resp.status_code != 200:
                        log.warning("The Odds API %s -> HTTP %s", key, resp.status_code)
                        continue
                    for ev in resp.json():
                        home, away = ev.get("home_team"), ev.get("away_team")
                        if not home or not away:
                            continue
                        bookmakers = []
                        for bm in ev.get("bookmakers", []):
                            for mk in bm.get("markets", []):
                                if mk.get("key") != "h2h":
                                    continue
                                odds = _map_h2h_outcomes(mk.get("outcomes", []),
                                                         home, away, group)
                                if odds:
                                    bookmakers.append({
                                        "key": bm.get("key", ""),
                                        "title": bm.get("title", ""),
                                        "odds": odds})
                        if not bookmakers:
                            continue
                        match = {
                            "id": ev.get("id", f"{key}-{home}-{away}"),
                            "sport_key": key,
                            "sport_group": group,
                            "league": (ev.get("sport_key") or key).replace("_", " ").title(),
                            "commence_time": ev.get("commence_time", ""),
                            "home_team": home,
                            "away_team": away,
                            "bookmakers": bookmakers,
                            "source": "live",
                        }
                        _attach_ratings(match, ratings)
                        matches.append(match)
    except Exception as exc:  # noqa: BLE001 - cualquier fallo usa la demo
        log.warning("Fallo al consultar The Odds API (%s); usando dataset demo", exc)
        return load_sample_matches(), "sample"
    if not matches:
        return load_sample_matches(), "sample"
    # Deportes sin cobertura en vivo (outright demo o fuera de temporada):
    # se completan con el dataset de demostración para no perderlos del radar.
    grupos_vivos = {m["sport_group"] for m in matches}
    for m in load_sample_matches():
        if m["sport_group"] not in grupos_vivos:
            matches.append(m)
    return matches, "live"


def get_matches() -> tuple[list[dict], str]:
    """Compatibilidad: lo mismo que fetch_live_matches."""
    return fetch_live_matches()
