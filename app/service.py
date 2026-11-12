"""Servicio de predicciones y recomendaciones.

Pipeline para cada partido:

    Elo (por deporte)
        -> probabilidades del modelo (Poisson en fútbol, Elo en basket/tenis)
        -> desvigado de las cuotas de cada casa (método de potencias)
        -> consenso de mercado + mejor cuota disponible
        -> edge, valor esperado, confianza bayesiana y Kelly fraccional
        -> filtro de valor (edge mínimo del plan) y explicación
"""

from __future__ import annotations

import copy
import statistics
import time
from typing import Any

from . import config, db, explain, providers
from .engine import devig, elo as elo_mod, ev, kelly as kelly_mod, poisson

# Configuración Elo por deporte (localía en puntos de rating).
ELO_BY_SPORT = {
    "soccer": elo_mod.EloConfig(k=24.0, home_advantage=60.0),
    "basketball": elo_mod.EloConfig(k=32.0, home_advantage=50.0),
    "tennis": elo_mod.EloConfig(k=20.0, home_advantage=20.0),
    # NFL/NCAA: la localía vale ~2.5-3 puntos reales -> ~40 pts Elo.
    "americanfootball": elo_mod.EloConfig(k=24.0, home_advantage=40.0),
    # Boxeo: terreno neutral, sin ventaja de localía.
    "boxing": elo_mod.EloConfig(k=20.0, home_advantage=0.0),
    # Béisbol MLB: el local gana ~53% de las veces -> ~25 pts Elo.
    "baseball": elo_mod.EloConfig(k=24.0, home_advantage=25.0),
    # Hockey NHL: localía ~55% -> ~30 pts Elo.
    "hockey": elo_mod.EloConfig(k=24.0, home_advantage=30.0),
    # Outright (F1, MotoGP, caballos): carrera en circuito/pista neutral.
    "formula1": elo_mod.EloConfig(k=24.0, home_advantage=0.0),
    "motogp": elo_mod.EloConfig(k=24.0, home_advantage=0.0),
    "horseracing": elo_mod.EloConfig(k=20.0, home_advantage=0.0),
}


def _selection_label(match: dict, selection: str) -> str:
    """Etiqueta legible de la selección (siempre con el nombre del equipo)."""
    # Outright: la selección ya es el nombre del participante.
    if match.get("participants") and selection in match["participants"]:
        return selection
    if match["sport_group"] == "soccer":
        if selection == "home":
            return f"Victoria de {match['home_team']}"
        if selection == "away":
            return f"Victoria de {match['away_team']}"
        return f"Empate ({match['home_team']} vs {match['away_team']})"
    return match["home_team"] if selection == "home" else match["away_team"]


MIN_ODDS = 1.25
MIN_CONFIDENCE = 0.55


def _elo_expected(group: str, home: str, away: str,
                  elo_home: float, elo_away: float) -> float:
    ratings = elo_mod.EloRatings({home: elo_home, away: elo_away},
                                 config=ELO_BY_SPORT[group])
    return ratings.expected(home, away)


def predict(match: dict, lang: str = "es") -> tuple[dict[str, float], dict[str, Any]]:
    """Probabilidades del modelo para un partido + metadatos explicativos."""
    group = match["sport_group"]
    home, away = match["home_team"], match["away_team"]
    elo_home = float(match.get("elo_home", 1500.0))
    elo_away = float(match.get("elo_away", 1500.0))
    meta: dict[str, Any] = {"elo_home": elo_home, "elo_away": elo_away,
                            "model": _model_label(group, lang)}

    # Outright (F1, MotoGP, caballos): N participantes -> Bradley-Terry.
    # Con N=2 coincide exactamente con la logística Elo de2 competidores.
    parts = match.get("participants") or []
    if parts:
        ratings = match.get("elo_participants") or {p: 1500.0 for p in parts}
        strengths = {p: 10.0 ** (float(ratings.get(p, 1500.0)) / 400.0)
                     for p in parts}
        total = sum(strengths.values())
        probs = {p: s / total for p, s in strengths.items()}
        best = max(probs, key=probs.get)
        values = [float(v) for v in ratings.values()]
        meta["elo_home"] = max(values)      # mejor rating del campo (display)
        meta["elo_away"] = sum(values) / len(values)  # media del campo
        meta["field_size"] = len(parts)
        meta["elo_participants"] = {p: float(ratings.get(p, 1500.0))
                                    for p in parts}
        if lang == "en":
            meta["model_detail"] = (
                f"Bradley-Terry over Elo of {len(parts)} entrants; "
                f"favourite {best} at {probs[best] * 100:.1f}%")
        else:
            meta["model_detail"] = (
                f"Bradley-Terry sobre Elo de {len(parts)} participantes; "
                f"favorito {best} con {probs[best] * 100:.1f}%")
        return probs, meta

    if group == "soccer":
        lam_h, lam_a = poisson.expected_lambdas(elo_home, elo_away)
        probs = poisson.match_probabilities(lam_h, lam_a)
        score_i, score_j, score_p = poisson.most_likely_score(lam_h, lam_a)
        if lang == "en":
            meta["model_detail"] = (
                f"λ_home={lam_h:.2f}, λ_away={lam_a:.2f}; "
                f"most likely score {score_i}-{score_j} ({score_p * 100:.1f}%)")
        else:
            meta["model_detail"] = (
                f"λ_local={lam_h:.2f}, λ_visitante={lam_a:.2f}; "
                f"marcador más probable {score_i}-{score_j} ({score_p * 100:.1f}%)")
        meta["market_lines"] = {k: round(v, 4) for k, v in probs.items()
                                if k.startswith(("btts", "over", "lambda"))}
        return {"home": probs["home"], "draw": probs["draw"],
                "away": probs["away"]}, meta

    p_home = _elo_expected(group, home, away, elo_home, elo_away)
    meta["model_detail"] = ""
    return {"home": p_home, "away": 1.0 - p_home}, meta


def _model_label(group: str, lang: str) -> str:
    if lang == "en":
        return explain.MODEL_LABELS_EN[group]
    return explain.MODEL_LABELS[group]


def _market_probs(match: dict) -> tuple[dict[str, dict[str, float]], dict[str, list[float]]]:
    """Desvigado por casa y probabilidades sin vig por selección.

    Devuelve (por_casa, por_seleccion_conservadas_para_sigma).
    """
    per_book: dict[str, dict[str, float]] = {}
    by_selection: dict[str, list[float]] = {}
    for bm in match["bookmakers"]:
        odds = bm.get("odds", {})
        if len(odds) < 2:
            continue
        keys = list(odds.keys())
        probs, _m = devig.remove_vig([odds[k] for k in keys], method="power")
        per_book[bm["key"]] = dict(zip(keys, probs))
        for k, p in zip(keys, probs):
            by_selection.setdefault(k, []).append(p)
    return per_book, by_selection


def evaluate_match(match: dict, bankroll: float | None = None, lang: str = "es") -> list[dict]:
    """Todas las selecciones con valor de un partido (pueden ser 0)."""
    bankroll = bankroll or config.DEFAULT_BANKROLL
    group = match["sport_group"]
    # Outright: las selecciones son los participantes del evento.
    selections = match.get("participants") or providers.SELECTIONS.get(group, [])
    model_probs, meta = predict(match, lang)
    per_book, by_selection = _market_probs(match)
    if not per_book:
        return []

    out: list[dict] = []
    for sel in selections:
        if sel not in model_probs:
            continue
        # Mejor cuota disponible para esta selección.
        offers = {bm["key"]: bm["odds"][sel] for bm in match["bookmakers"]
                  if sel in bm.get("odds", {})}
        if not offers:
            continue
        book, odds = devig.best_odds(offers)
        if odds < MIN_ODDS:
            continue

        p_model = model_probs[sel]
        market_list = by_selection.get(sel, [])
        if not market_list:
            continue
        p_market = sum(market_list) / len(market_list)
        implied = 1.0 / odds
        edge = ev.edge(p_model, p_market)
        expect = ev.expected_value(p_model, odds)
        conf = ev.confidence(p_model, p_market, market_list,
                             n_eff=config.EFFECTIVE_N)
        k = kelly_mod.recommended_stake(
            p_model, odds, bankroll,
            fraction=config.KELLY_FRACTION,
            max_stake_pct=config.MAX_STAKE_PCT / 100.0)
        _m_per_book = {k_: v.get(sel) for k_, v in per_book.items() if sel in v}
        # Margen de la casa que ofrece la mejor cuota (mercado completo).
        book_odds = next((b["odds"] for b in match["bookmakers"]
                          if b["key"] == book), {sel: odds})
        market_margin = devig.margin(list(book_odds.values())) if len(book_odds) >= 2 else 0.0

        out.append({
            "match_id": match["id"],
            "sport": group,
            "sport_key": match.get("sport_key", group),
            "league": explain.translate_league(match.get("league", ""), lang),
            "commence_time": match.get("commence_time", ""),
            "home_team": match["home_team"],
            "away_team": match["away_team"],
            "selection": sel,
            "selection_label": _selection_label(match, sel),
            "bookmaker": book,
            "odds": odds,
            "implied_prob": implied,
            "margin": market_margin,
            "market_prob": p_market,
            "model_prob": p_model,
            "edge": edge,
            "ev": expect,
            "confidence": conf,
            "kelly": k,
            "books_count": len(market_list),
            "market_spread": ev.market_sigma(market_list),
            "elo_home": meta["elo_home"],
            "elo_away": meta["elo_away"],
            "market_type": "outright" if match.get("participants") else "h2h",
            "event": match.get("event", ""),
            "model": meta["model"],
            "model_detail": meta.get("model_detail", ""),
            "market_lines": meta.get("market_lines", {}),
            "_per_book_market": {k_: round(v, 4) for k_, v in _m_per_book.items()},
        })
        if match.get("participants"):
            # Contexto outright: tamaño del campo y rating del participante.
            rec = out[-1]
            rec["field_size"] = len(match["participants"])
            rec["elo_selection"] = meta["elo_participants"].get(sel, 1500.0)
    return out


# Caché en memoria de picks para el plan Free (retraso de 2 h).
# Clave: filtro de deporte (o "all"). Valor: (timestamp, picks).
_FREE_PICKS_CACHE: dict[str, tuple[float, list[dict]]] = {}
_FREE_DELAY_SECONDS = 2 * 3600  # 2 horas


def _cache_key(sport: str | None) -> str:
    return sport or "all"


def _get_cached_free_picks(sport_key: str) -> tuple[list[dict] | None, bool]:
    """Devuelve (picks, is_delayed) si hay caché válido.

    - is_delayed=True si los picks tienen más de 2 h (son "viejos").
    - is_delayed=False si son recientes (primera generación).
    """
    entry = _FREE_PICKS_CACHE.get(sport_key)
    if entry is None:
        return None, False
    ts, picks = entry
    age = time.time() - ts
    # Dentro de las 2 h: devolver los mismos (marcados como delayed).
    # Después de 2 h: caché caducada, hay que regenerar.
    if age < _FREE_DELAY_SECONDS:
        return copy.deepcopy(picks), True
    return None, False


def _clear_picks_cache() -> None:
    _FREE_PICKS_CACHE.clear()


def _store_free_picks(sport_key: str, picks: list[dict]) -> None:
    _FREE_PICKS_CACHE[sport_key] = (time.time(), copy.deepcopy(picks))


def _rank(candidates: list[dict]) -> list[dict]:
    """Ordena por valor ponderado por confianza."""
    for c in candidates:
        c["score"] = round(c["edge"] * (0.5 + 0.5 * c["confidence"]), 5)
    return sorted(candidates, key=lambda c: c["score"], reverse=True)


def _select_free_picks(ranked: list[dict], max_picks: int) -> list[dict]:
    """Curaduría del plan Free: 2+2+1 por nivel de demanda.

    Garantiza variedad: no más de 2 por deporte y cobertura de los tres
    niveles de demanda (estrella, media, nicho). Si un nivel no tiene
    candidatos, se rellena con los mejores disponibles.
    """
    quota = config.FREE_TIER_QUOTA
    selected_ids: set[str] = set()
    selected: list[dict] = []

    for tier in ("high", "medium", "low"):
        target = quota.get(tier, 0)
        count = 0
        sports_used: set[str] = set()
        # Primera pasada: preferir deportes distintos dentro del nivel.
        for c in ranked:
            if len(selected) >= max_picks:
                break
            if c["match_id"] in selected_ids:
                continue
            if config.SPORT_DEMAND.get(c["sport"], "medium") != tier:
                continue
            if c["sport"] in sports_used:
                continue
            selected.append(c)
            selected_ids.add(c["match_id"])
            sports_used.add(c["sport"])
            count += 1
            if count >= target:
                break
        # Segunda pasada: completar cupo con el mismo deporte si hace falta.
        if count < target:
            for c in ranked:
                if len(selected) >= max_picks:
                    break
                if c["match_id"] in selected_ids:
                    continue
                if config.SPORT_DEMAND.get(c["sport"], "medium") != tier:
                    continue
                selected.append(c)
                selected_ids.add(c["match_id"])
                count += 1
                if count >= target:
                    break

    # Relleno final con los mejores disponibles si aún hay hueco.
    for c in ranked:
        if len(selected) >= max_picks:
            break
        if c["match_id"] in selected_ids:
            continue
        selected.append(c)
        selected_ids.add(c["match_id"])

    selected.sort(key=lambda c: c.get("score", 0), reverse=True)
    return selected[:max_picks]
    """Ordena por valor ponderado por confianza."""
    for c in candidates:
        c["score"] = round(c["edge"] * (0.5 + 0.5 * c["confidence"]), 5)
    return sorted(candidates, key=lambda c: c["score"], reverse=True)


def _attach_evidence(recs: list[dict], conn) -> dict[str, dict]:
    """Backtest por deporte para sustentar cada recomendación."""
    history = db.fetch_history(conn)
    evidence: dict[str, dict] = {}
    for sport in {r["sport"] for r in recs} | {"all"}:
        subset = history if sport == "all" else [h for h in history if h["sport"] == sport]
        evidence[sport] = explain.performance_summary(subset, None if sport == "all" else sport)
    return evidence


def build_recommendations(plan: str = "free", sport: str | None = None,
                          min_edge: float | None = None,
                          bankroll: float | None = None,
                          matches: list[dict] | None = None,
                          source: str | None = None,
                          conn=None, lang: str = "es") -> dict[str, Any]:
    """Pipeline completo -> recomendaciones rankeadas y explicadas."""
    if lang not in explain.SUPPORTED_LANGS:
        lang = "es"
    plan_cfg = config.PLANS.get(plan, config.PLANS["free"])
    threshold = plan_cfg["min_edge"] if min_edge is None else min_edge
    max_picks = plan_cfg["max_picks"]

    if matches is None:
        matches, source = providers.get_matches()
    if sport:
        matches = [m for m in matches if m["sport_group"] == sport]

    close_conn = conn is None
    if conn is None:
        conn = db.connect()
    try:
        candidates: list[dict] = []
        for m in matches:
            candidates.extend(evaluate_match(m, bankroll=bankroll, lang=lang))
        candidates = [c for c in candidates
                      if c["edge"] >= threshold
                      and c["ev"] > 0
                      and c["confidence"] >= MIN_CONFIDENCE]
        ranked = _rank(candidates)

        # Un solo pick por partido (la mejor selección de cada uno).
        seen: set[str] = set()
        picks: list[dict] = []
        is_delayed = False

        cache_key = f"{_cache_key(sport)}:{lang}"
        use_cache = (plan == "free")

        if use_cache:
            cached, is_delayed = _get_cached_free_picks(cache_key)
            if cached is not None:
                picks = cached
            else:
                deduped: list[dict] = []
                seen2: set[str] = set()
                for c in ranked:
                    if c["match_id"] in seen2:
                        continue
                    seen2.add(c["match_id"])
                    deduped.append(c)
                picks = _select_free_picks(deduped, max_picks)
                _store_free_picks(cache_key, picks)
                is_delayed = False
        elif plan == "free":
            deduped = []
            seen2 = set()
            for c in ranked:
                if c["match_id"] in seen2:
                    continue
                seen2.add(c["match_id"])
                deduped.append(c)
            picks = _select_free_picks(deduped, max_picks)
        else:
            for c in ranked:
                if c["match_id"] in seen:
                    continue
                seen.add(c["match_id"])
                picks.append(c)
                if len(picks) >= max_picks:
                    break

        evidence = _attach_evidence(picks, conn)
        for p in picks:
            stats = evidence.get(p["sport"], evidence["all"])
            p["backtest"] = {k: round(v, 4) for k, v in stats.items()
                             if k not in ("equity_curve", "sport")}
            p["explanation"] = explain.build_explanation(
                p, stats, stats.get("bets", 0), lang=lang)
            p.pop("_per_book_market", None)
            p["tier"] = plan
            p["score"] = round(p["score"], 4)
            if not plan_cfg["full_analysis"]:
                # Free: modelo, mercado y valor; Kelly/backtest en Premium.
                p["explanation"]["steps"] = p["explanation"]["steps"][:3]
                p["explanation"]["locked_note"] = (
                    "Kelly stake, entry timing, confidence and full backtest "
                    "are in the Premium plan." if lang == "en" else
                    "Stake Kelly, cuándo entrar, confianza y backtest "
                    "completos en el plan Premium.")
                p.pop("backtest", None)
                # Ocultar detalles premium (opción A+B).
                p["delayed"] = is_delayed
                p["locked_fields"] = ["kelly", "confidence", "odds",
                                      "backtest", "model_prob", "market_prob"]
                for field in ("kelly", "confidence", "odds", "model_prob",
                              "market_prob", "implied_prob", "margin",
                              "market_spread", "books_count", "elo_home",
                              "elo_away", "market_lines", "market_type",
                              "event"):
                    p.pop(field, None)
            else:
                p["delayed"] = False
                p["locked_fields"] = []

        return {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source": source or "sample",
            "plan": plan,
            "min_edge": threshold,
            "models_scanned": len(matches),
            "value_candidates": len(candidates),
            "count": len(picks),
            "picks": picks,
        }
    finally:
        if close_conn:
            conn.close()


def matches_overview(matches: list[dict] | None = None, lang: str = "es") -> list[dict]:
    """Partidos con probabilidades de modelo y de mercado (sin filtro de valor)."""
    if matches is None:
        matches, _src = providers.get_matches()
    out = []
    for m in matches:
        model_probs, meta = predict(m, lang)
        per_book, by_selection = _market_probs(m)
        cons = {k: (sum(v) / len(v)) if v else None for k, v in by_selection.items()}
        best = {}
        for sel in by_selection:
            offers = {bm["key"]: bm["odds"][sel] for bm in m["bookmakers"]
                      if sel in bm.get("odds", {})}
            if offers:
                b, o = devig.best_odds(offers)
                best[sel] = {"bookmaker": b, "odds": o,
                             "edge": round(model_probs.get(sel, 0) - cons[sel], 4)
                             if cons.get(sel) is not None else None}
        out.append({
            "id": m["id"], "sport": m["sport_group"],
            "sport_key": m.get("sport_key"),
            "league": explain.translate_league(m.get("league") or "", lang),
            "commence_time": m.get("commence_time"),
            "home_team": m["home_team"], "away_team": m["away_team"],
            "event": m.get("event", ""),
            "market_type": "outright" if m.get("participants") else "h2h",
            "field_size": len(m.get("participants") or []),
            "elo_home": meta["elo_home"], "elo_away": meta["elo_away"],
            "model": meta["model"],
            "model_detail": meta.get("model_detail", ""),
            "model_probabilities": {k: round(v, 4) for k, v in model_probs.items()},
            "market_probabilities": {k: round(v, 4) for k, v in cons.items() if v is not None},
            "best_offers": best,
            "books": len(per_book),
        })
    return out


def consensus_line(match: dict) -> dict[str, float]:
    """Línea consensuada (prob. sin vig) por selección."""
    _per_book, by_selection = _market_probs(match)
    return {k: statistics.fmean(v) for k, v in by_selection.items() if v}
