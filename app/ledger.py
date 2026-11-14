"""Registro público de picks: append-only y con cadena de hashes.

Principio: una vez publicado un pick, **no se puede editar ni borrar**.
Cada fila guarda el hash de la fila anterior (``prev_hash``) y su propio
hash (``row_hash``), calculado sobre sus campos canónicos. Cualquier
edición, borrado o reordenación rompe la cadena y ``verify()`` lo detecta.

Tres cadenas independientes, ancladas juntas una vez al día:

- ``picks``          lo que se publicó ANTES de cada evento.
- ``pick_closings``  la cuota de cierre congelada y el CLV calculado.
- ``pick_results``   el resultado real (ganada/perdida/empate/nula).

El ancla diaria (``ledger_anchors``) resume las tres cabezas en un solo
hash: es lo que se publica para que un tercero pueda comparar sin confiar
en nosotros.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import threading
import time
from typing import Any

from . import config, db
from .engine import backtest as bt
from .engine import devig

log = logging.getLogger("apuesta_edge.ledger")

# Un solo candado por proceso: la cadena exige que la última fila no cambie
# entre leer el hash anterior y escribir la nueva.
_CHAIN_LOCK = threading.Lock()

_PICK_FIELDS = (
    "pick_key", "event_id", "sport_key", "created_at", "event_start", "sport",
    "league", "event", "market", "selection", "selection_label", "bookmaker",
    "bet_odds", "model_prob", "market_prob", "edge", "stake_units",
    "model_version", "source")

_PICK_FLOATS = frozenset({"created_at", "event_start", "bet_odds",
                          "model_prob", "market_prob", "edge", "stake_units"})

_CLOSING_FIELDS = ("pick_id", "closing_odds", "closing_at", "clv_pct")
_CLOSING_FLOATS = frozenset({"pick_id", "closing_odds", "closing_at", "clv_pct"})

_RESULT_FIELDS = ("pick_id", "result", "profit_units", "settled_at")
_RESULT_FLOATS = frozenset({"pick_id", "profit_units", "settled_at"})

_FIELDS = {
    "picks": (_PICK_FIELDS, _PICK_FLOATS),
    "pick_closings": (_CLOSING_FIELDS, _CLOSING_FLOATS),
    "pick_results": (_RESULT_FIELDS, _RESULT_FLOATS),
}

VALID_RESULTS = ("won", "lost", "push", "void")


# ------------------------------------------------------------------ hashing
def _normalize(table: str, row: dict) -> dict:
    fields, floats = _FIELDS[table]
    out: dict[str, Any] = {}
    for key in fields:
        value = row.get(key)
        if value is None:
            out[key] = None
        elif key in floats:
            out[key] = float(value)
        elif key == "pick_id":
            out[key] = int(value)
        else:
            out[key] = str(value)
    return out


def _canonical(table: str, row: dict) -> str:
    return json.dumps(_normalize(table, row), sort_keys=True,
                      separators=(",", ":"), ensure_ascii=False)


def _row_hash(prev_hash: str, canonical: str) -> str:
    return hashlib.sha256((prev_hash + canonical).encode("utf-8")).hexdigest()


def append(table: str, conn, values: dict) -> bool:
    """Añade una fila a la cadena. ``False`` si ya existía (idempotente)."""
    with _CHAIN_LOCK:
        prev_hash = db.ledger_last_hash(conn, table)
        row_hash = _row_hash(prev_hash, _canonical(table, values))
        return db.ledger_insert(conn, table,
                                {**values, "prev_hash": prev_hash,
                                 "row_hash": row_hash})


# ------------------------------------------------------------------- picks
def append_pick(conn, rec: dict, *, created_at: float | None = None,
                model_version: str | None = None,
                source: str = "live") -> bool:
    """Publica un pick. ``pick_key`` = id del evento: uno por evento.

    Un evento ya publicado no se puede "re-elegir" aunque la cuota mejore:
    eso sería reescribir el pasado.
    """
    values = {
        "pick_key": str(rec["match_id"]),
        "event_id": str(rec["match_id"]),
        "sport_key": str(rec.get("sport_key") or rec.get("sport", "")),
        "created_at": time.time() if created_at is None else float(created_at),
        "event_start": _iso_ts(rec.get("commence_time")),
        "sport": str(rec.get("sport", "")),
        "league": str(rec.get("league_raw") or rec.get("league", "")),
        "event": str(rec.get("event") or
                     f"{rec.get('home_team', '')} vs {rec.get('away_team', '')}"),
        "market": str(rec.get("market_type")
                      or ("outright" if rec.get("field_size") else "h2h")),
        "selection": str(rec["selection"]),
        "selection_label": str(rec.get("selection_label", rec["selection"])),
        "bookmaker": str(rec.get("bookmaker", "")),
        "bet_odds": float(rec["odds"]),
        "model_prob": float(rec["model_prob"]),
        "market_prob": float(rec["market_prob"]),
        "edge": float(rec["edge"]),
        "stake_units": float((rec.get("kelly") or {}).get("stake_pct") or 0.0),
        "model_version": model_version or config.MODEL_VERSION,
        "source": source,
    }
    return append("picks", conn, values)


def publish(conn, matches: list[dict], source: str, *,
            now: float | None = None, min_edge: float | None = None) -> int:
    """Guarda los picks con valor de este parte. Solo con datos reales.

    Con ``source != "live"`` no se publica nada: el registro público nunca
    mezcla eventos reales con demostración.
    """
    if source != "live" or not matches:
        return 0
    from . import service  # import local: service ya importa providers
    now = time.time() if now is None else now
    added = 0
    for rec in service.candidates_for_ledger(
            matches, min_edge=min_edge, now=now):
        if append_pick(conn, rec, created_at=now, source=source):
            added += 1
    return added


# ---------------------------------------------------------------- cierres
def clv_pct(bet_odds: float, closing_odds: float | None) -> float | None:
    """CLV = (cuota apostada / cuota de cierre − 1) × 100.

    Positivo = entramos mejor que el cierre (la métrica que de verdad
    predice rentabilidad). ``None`` si no hay cierre válido.
    """
    if not closing_odds or closing_odds <= 1.0 or not bet_odds:
        return None
    return (float(bet_odds) / float(closing_odds) - 1.0) * 100.0


def _best_odds_for(match: dict, selection: str) -> float | None:
    offers = {bm["key"]: bm["odds"][selection] for bm in match.get("bookmakers", [])
              if selection in bm.get("odds", {})}
    if not offers:
        return None
    _book, odds = devig.best_odds(offers)
    return float(odds)


def capture_closings(conn, matches: list[dict], *,
                     now: float | None = None,
                     window: int | None = None) -> int:
    """Congela la cuota de cierre de los picks que están por empezar."""
    now = time.time() if now is None else now
    window = config.LEDGER_CLOSE_WINDOW if window is None else window
    by_id = {str(m.get("id")): m for m in matches or []}
    pending = db.ledger_pending_closings(
        conn, until_ts=now + window, after_ts=now - 3600.0)
    added = 0
    for pick in pending:
        match = by_id.get(str(pick["event_id"]))
        if not match:
            continue
        odds = _best_odds_for(match, pick["selection"])
        if odds is None:
            continue
        clv = clv_pct(pick["bet_odds"], odds)
        if clv is None:
            continue
        if append("pick_closings", conn, {
                "pick_id": int(pick["id"]), "closing_odds": odds,
                "closing_at": now, "clv_pct": clv}):
            added += 1
    return added


# --------------------------------------------------------------- resultados
def outcome_for(selection: str, home_score: int, away_score: int,
                sport: str = "") -> str | None:
    """Resultado de una selección h2h según el marcador final.

    ``None`` = no se puede determinar (outright, marcador desconocido):
    el pick se queda pendiente antes que inventar un resultado.
    """
    if home_score is None or away_score is None:
        return None
    if selection == "draw":
        return "won" if home_score == away_score else "lost"
    if selection not in ("home", "away"):
        return None
    tied = home_score == away_score
    if selection == "home":
        won = home_score > away_score
    else:
        won = away_score > home_score
    if tied and sport and sport != "soccer":
        return "push"
    return "won" if won else "lost"


def profit_units_for(result: str, stake_units: float,
                     bet_odds: float) -> float:
    """Beneficio en unidades (1 u = 1% del bankroll), sin redondear."""
    if result == "won":
        return float(stake_units) * (float(bet_odds) - 1.0)
    if result == "lost":
        return -float(stake_units)
    return 0.0  # push / void


def settle(conn, scores: dict[str, dict], *, now: float | None = None) -> int:
    """Asienta los picks cuyo evento ya terminó, usando marcadores reales."""
    now = time.time() if now is None else now
    pending = db.ledger_pending_results(
        conn, before_ts=now, after_ts=now - config.LEDGER_SETTLE_WINDOW)
    added = 0
    for pick in pending:
        score = scores.get(str(pick["event_id"]))
        if not score or not score.get("completed"):
            continue
        result = outcome_for(pick["selection"], score.get("home"),
                             score.get("away"), pick.get("sport", ""))
        if result is None:
            continue
        profit = profit_units_for(result, pick["stake_units"], pick["bet_odds"])
        if append("pick_results", conn, {
                "pick_id": int(pick["id"]), "result": result,
                "profit_units": profit, "settled_at": now}):
            added += 1
    return added


# ---------------------------------------------------------------- resumen
def summary(conn, *, league: str | None = None) -> dict:
    """Métricas públicas calculadas SOLO sobre picks asentados.

    Los pendientes se cuentan aparte y nunca se presentan como resultado.
    """
    settled = db.ledger_settled(conn)
    if league:
        settled = [r for r in settled if r["league"] == league]
    counts = db.ledger_counts(conn)
    total = counts["picks_count"]

    decided = [r for r in settled if r["result"] in ("won", "lost")]
    stakes = [float(r["stake_units"]) for r in decided]
    profits = [float(r["profit_units"]) for r in decided]
    results = [1 if r["result"] == "won" else 0 for r in decided]
    odds = [float(r["bet_odds"]) for r in decided]
    clv = [float(r["clv_pct"]) for r in settled
           if r["clv_pct"] is not None]

    stats = bt.summarize(stakes, profits, results, odds, clv) if decided else None
    equity, points, running = [], [], 0.0
    for row in settled:
        running += float(row["profit_units"])
        equity.append(round(running, 3))
        points.append({"ts": float(row["settled_at"]),
                       "profit_units": round(running, 4)})

    out = {
        "sample": len(decided),
        "picks_total": total,
        "pending": max(0, total - len(settled)),
        "losses": sum(1 for r in settled if r["result"] == "lost"),
        "wins": sum(1 for r in settled if r["result"] == "won"),
        "pushes": sum(1 for r in settled if r["result"] == "push"),
        "voids": sum(1 for r in settled if r["result"] == "void"),
        "avg_clv_pct": round(stats["avg_clv_pct"], 3) if stats else 0.0,
        "clv_sample": len(clv),
        "roi_pct": round(stats["roi_pct"], 2) if stats else 0.0,
        "hit_rate_pct": round(stats["hit_rate_pct"], 2) if stats else 0.0,
        "profit_units": round(sum(profits), 3),
        "max_drawdown_units": round(stats["max_drawdown_units"], 3) if stats else 0.0,
        "binomial_p_value": round(stats["binomial_p_value"], 6) if stats else 1.0,
        "avg_odds": round(stats["avg_odds"], 3) if stats else 0.0,
        "breakeven_hit_pct": round(stats["breakeven_hit_pct"], 2) if stats else 0.0,
        "since": min((float(r["created_at"]) for r in settled), default=None),
        "last_settled_at": (max(float(r["settled_at"]) for r in settled)
                            if settled else None),
        "equity_curve": equity,
        "equity_points": points,
        "pending_note": ("Muestra insuficiente: se necesitan al menos 30 picks "
                         "asentados para leer estas cifras como señal."
                         if len(decided) < 30 else ""),
    }
    return out


def by_league(conn) -> dict[str, dict]:
    """Resumen por liga (para el dashboard). Ligas con muestra pequeña aparte."""
    settled = db.ledger_settled(conn)
    leagues = sorted({r["league"] for r in settled})
    counts = db.ledger_counts(conn)["picks_count"]
    out: dict[str, dict] = {}
    for league in leagues:
        rows = [r for r in settled if r["league"] == league]
        decided = [r for r in rows if r["result"] in ("won", "lost")]
        stakes = [float(r["stake_units"]) for r in decided]
        profits = [float(r["profit_units"]) for r in decided]
        results = [1 if r["result"] == "won" else 0 for r in decided]
        odds = [float(r["bet_odds"]) for r in decided]
        clv = [float(r["clv_pct"]) for r in rows if r["clv_pct"] is not None]
        stats = bt.summarize(stakes, profits, results, odds, clv) if decided else {}
        out[league] = {
            "picks": len(rows),
            "sample": len(decided),
            "wins": sum(results),
            "losses": len(decided) - sum(results),
            "hit_rate_pct": round(stats.get("hit_rate_pct", 0.0), 2),
            "roi_pct": round(stats.get("roi_pct", 0.0), 2),
            "avg_clv_pct": round(stats.get("avg_clv_pct", 0.0), 3),
            "clv_sample": len(clv),
            "binomial_p_value": round(stats.get("binomial_p_value", 1.0), 6),
            "significant": (len(decided) >= 30
                            and stats.get("binomial_p_value", 1.0) < 0.05),
        }
    out["_total_picks"] = counts
    return out


# ------------------------------------------------------------ verificación
def verify(conn) -> dict:
    """Recalcula las tres cadenas. Detecta ediciones y borrados."""
    report: dict[str, Any] = {"ok": True, "chains": {}}
    for table in ("picks", "pick_closings", "pick_results"):
        prev = ""
        rows = db.ledger_rows(conn, table)
        for row in rows:
            expected = _row_hash(prev, _canonical(table, row))
            if row["prev_hash"] != prev or row["row_hash"] != expected:
                report["ok"] = False
                report["chains"][table] = {
                    "ok": False, "rows": len(rows), "broken_at": row["id"],
                    "reason": ("prev_hash no enlaza" if row["prev_hash"] != prev
                               else "row_hash no coincide: fila editada")}
                break
            prev = row["row_hash"]
        else:
            report["chains"][table] = {"ok": True, "rows": len(rows),
                                       "head": prev}
    return report


def anchor(conn, *, day: str | None = None,
           now: float | None = None, save: bool = True) -> dict:
    """Ancla diaria: un hash que resume las tres cabezas del registro."""
    now = time.time() if now is None else now
    day = day or time.strftime("%Y-%m-%d", time.gmtime(now))
    counts = db.ledger_counts(conn)
    material = "|".join(str(counts[f"{k}_{s}"])
                        for k in ("picks", "closings", "results")
                        for s in ("head", "count"))
    payload = {
        "day": day,
        "picks_head": counts["picks_head"],
        "picks_count": counts["picks_count"],
        "closings_head": counts["closings_head"],
        "closings_count": counts["closings_count"],
        "results_head": counts["results_head"],
        "results_count": counts["results_count"],
        "head_hash": hashlib.sha256(material.encode("utf-8")).hexdigest(),
        "published_at": now,
    }
    if save:
        db.ledger_anchor_save(conn, payload)
    return payload


def _iso_ts(value: Any) -> float | None:
    """ISO-8601 (``2026-11-15T16:30:00Z``) -> epoch. ``None`` si no válido."""
    if not value:
        return None
    try:
        import datetime as dt
        return dt.datetime.fromisoformat(
            str(value).replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError):
        return None


# ------------------------------------------------------------ tarea de fondo
def cycle(matches_provider=None, *, now: float | None = None,
          scores_fetcher=None) -> dict:
    """Un ciclo completo: publicar, congelar cierres, asentar y anclar.

    Es idempotente: repetirlo no duplica filas ni reescribe nada.
    """
    from . import providers
    now = time.time() if now is None else now
    if matches_provider is None:
        matches, source = providers.fetch_live_matches()
    else:
        matches, source = matches_provider()

    conn = db.connect()
    try:
        published = publish(conn, matches, source, now=now)
        closings = capture_closings(conn, matches, now=now)

        pending = db.ledger_pending_results(
            conn, before_ts=now,
            after_ts=now - config.LEDGER_SETTLE_WINDOW)
        keys = sorted({p["sport_key"] for p in pending if p["sport_key"]})
        scores: dict[str, dict] = {}
        fetcher = scores_fetcher or providers.fetch_scores
        for key in keys:
            scores.update(fetcher(key))
        settled = settle(conn, scores, now=now)

        day = time.strftime("%Y-%m-%d", time.gmtime(now))
        anchored = None
        if db.ledger_anchor_on(conn, day) is None:
            counts = db.ledger_counts(conn)
            if counts["picks_count"]:
                anchored = anchor(conn, day=day, now=now)

        return {"published": published, "closings": closings,
                "settled": settled, "anchored": bool(anchored),
                "source": source}
    finally:
        conn.close()


async def run_loop(matches_provider=None, interval: int | None = None) -> None:
    """Bucle del registro: primer ciclo a los 30 s y luego cada ``interval``."""
    interval = interval or config.LEDGER_PUBLISH_INTERVAL
    await asyncio.sleep(30)
    while True:
        try:
            result = await asyncio.to_thread(cycle, matches_provider)
            if any(result[k] for k in ("published", "closings", "settled")):
                log.info("[ledger] %s", result)
            if result["source"] != "live":
                log.info("[ledger] sin datos en vivo (%s): registro intacto",
                         result["source"])
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - un fallo no puede parar el registro
            log.exception("Error en el ciclo del registro")
        await asyncio.sleep(interval)
