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
import time
from typing import Any

import httpx

from . import config

log = logging.getLogger("apuesta_edge.providers")

SELECTIONS = {"soccer": ["home", "draw", "away"],
              "basketball": ["home", "away"],
              "tennis": ["home", "away"],
              "americanfootball": ["home", "away"],
              "boxing": ["home", "away"],
              "baseball": ["home", "away"],
              "hockey": ["home", "away"]}
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
    if sport_key.startswith("icehockey"):
        return "hockey"
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


# Diagnóstico de la última consulta a The Odds API (sin secretos):
# por qué se cayó al dataset de demo. Se expone en /api/health.
LAST_DIAG: dict[str, Any] = {}


# Descubrimiento de deportes en temporada (endpoint gratuito /sports,
# no consume créditos). Se usa para no pedir torneos fuera de temporada
# (ahorra créditos) y para localizar los torneos de tenis, que son claves
# individuales (no existe "tennis_atp" genérico).
_IN_SEASON_CACHE: dict[str, Any] = {"ts": 0.0, "keys": set()}
IN_SEASON_TTL = 6 * 3600.0


def in_season_keys(client) -> set[str]:
    """Claves de deportes en temporada; vacío si la consulta falla."""
    now = time.time()
    cached = _IN_SEASON_CACHE["keys"]
    if cached and now - _IN_SEASON_CACHE["ts"] < IN_SEASON_TTL:
        return cached
    try:
        resp = client.get("/sports", params={"apiKey": config.ODDS_API_KEY})
        if resp.status_code != 200:
            log.warning("The Odds API /sports -> HTTP %s", resp.status_code)
            return cached
        keys = {s.get("key") for s in resp.json() if s.get("key")}
        _IN_SEASON_CACHE.update(ts=now, keys=keys)
        return keys
    except Exception as exc:  # noqa: BLE001 - sin descubrimiento seguimos
        log.warning("No se pudo listar deportes en temporada (%s)", exc)
        return cached


def plan_keys(in_season: set[str]) -> list[tuple[str, list[str]]]:
    """Decide qué claves pedir por grupo.

    - Fuera de ``in_season`` no se piden (ahorra créditos y evita
      eventos vacíos). Si el descubrimiento falló (``in_season`` vacío)
      se usan las claves configuradas como respaldo.
    - El tenis se descubre: todos los torneos ``tennis_atp_*``/
      ``tennis_wta_*`` en temporada.
    """
    out: list[tuple[str, list[str]]] = []
    for group, keys in config.ODDS_API_SPORTS.items():
        if in_season:
            selected = [k for k in keys if k in in_season]
            if group == "tennis":
                selected += sorted(
                    k for k in in_season
                    if k.startswith(("tennis_atp_", "tennis_wta_")))
        else:
            selected = list(keys)
        if selected:
            out.append((group, selected))
    return out


def _track_quota(resp) -> None:
    """Registra el consumo de créditos reportado por la API (cabeceras)."""
    remaining = resp.headers.get("x-requests-remaining")
    used = resp.headers.get("x-requests-used")
    if remaining is not None:
        try:
            LAST_DIAG["quota_remaining"] = int(remaining)
        except ValueError:
            pass
    if used is not None:
        try:
            LAST_DIAG["quota_used"] = int(used)
        except ValueError:
            pass


def fetch_live_matches() -> tuple[list[dict] | None, str]:
    """Obtiene cuotas en vivo. Devuelve ``(matches, fuente)``.

    - Sin clave -> dataset de demostración (solo desarrollo local).
    - Con clave -> solo datos reales. Cualquier fallo devuelve
      ``(None, "error")`` para que el llamador use el último parte real
      guardado (o indique "sin datos"). JAMÁS se mezclan eventos de
      demostración con datos en vivo.
    """
    if not config.ODDS_API_KEY:
        LAST_DIAG.clear()
        LAST_DIAG["reason"] = "no_api_key"
        return load_sample_matches(), "sample"
    ratings = load_ratings()
    matches: list[dict] = []
    status_by_key: dict[str, Any] = {}
    LAST_DIAG.clear()
    LAST_DIAG["status_by_key"] = status_by_key
    try:
        with httpx.Client(base_url="https://api.the-odds-api.com/v4",
                          timeout=config.ODDS_API_TIMEOUT) as client:
            in_season = in_season_keys(client)
            LAST_DIAG["in_season_keys"] = len(in_season)
            for group, keys in plan_keys(in_season):
                for key in keys:
                    resp = client.get(
                        f"/sports/{key}/odds",
                        params={"apiKey": config.ODDS_API_KEY,
                                "regions": config.ODDS_API_REGION,
                                "markets": "h2h",
                                "oddsFormat": "decimal"})
                    _track_quota(resp)
                    status_by_key[key] = resp.status_code
                    if resp.status_code != 200:
                        body = resp.text[:160]
                        status_by_key[f"{key}_body"] = body
                        log.warning("The Odds API %s -> HTTP %s %s", key,
                                    resp.status_code, body)
                        continue
                    for ev in resp.json():
                        home, away = ev.get("home_team"), ev.get("away_team")
                        if not home or not away:
                            continue
                        # Solo partidos que el modelo puede evaluar: si
                        # falta el rating de alguno de los dos lados no se
                        # publica (evita "valor" falso con rating plano).
                        elo_home = ratings.get(home)
                        elo_away = ratings.get(away)
                        if elo_home is None or elo_away is None:
                            LAST_DIAG["skipped_no_rating"] = (
                                LAST_DIAG.get("skipped_no_rating", 0) + 1)
                            continue
                        bookmakers = []
                        for bm in ev.get("bookmakers", []):
                            for mk in bm.get("markets", []):
                                if mk.get("key") != "h2h":
                                    continue
                                odds = _map_h2h_outcomes(
                                    mk.get("outcomes", []), home, away, group)
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
                            "league": (ev.get("sport_title") or key
                                       ).replace("_", " "),
                            "commence_time": ev.get("commence_time", ""),
                            "home_team": home,
                            "away_team": away,
                            "elo_home": float(elo_home),
                            "elo_away": float(elo_away),
                            "bookmakers": bookmakers,
                            "source": "live",
                        }
                        matches.append(match)
    except Exception as exc:  # noqa: BLE001 - el llamador usa el respaldo
        LAST_DIAG["reason"] = f"exception: {exc}"
        log.warning("Fallo al consultar The Odds API (%s)", exc)
        return None, "error"
    LAST_DIAG["events_with_odds"] = len(matches)
    if not matches:
        LAST_DIAG.setdefault("reason", "no_events_with_odds")
        return None, "error"
    # Sin relleno de demostración: los deportes sin eventos en vivo
    # simplemente no aparecen hasta que los haya de verdad.
    return matches, "live"


def get_matches() -> tuple[list[dict], str]:
    """Compatibilidad: lo mismo que fetch_live_matches."""
    return fetch_live_matches()
