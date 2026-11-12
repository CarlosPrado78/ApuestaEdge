"""Generación de explicaciones en lenguaje natural para cada recomendación.

Cada pick incluye el "por qué": qué modelo se usó, qué dice el mercado,
cuál es el valor esperado, por qué confiar (confianza estadística +
backtest con test binomial) y qué riesgos conlleva.

Soporta ``lang="es"`` (por defecto) y ``lang="en"``.
"""

from __future__ import annotations

from typing import Any

from .engine import backtest as bt

SUPPORTED_LANGS = ("es", "en")

SPORT_LABELS = {"soccer": "Fútbol", "basketball": "Básquet", "tennis": "Tenis",
                       "americanfootball": "Fútbol americano",
                       "boxing": "Boxeo", "baseball": "Béisbol",
                       "hockey": "Hockey (NHL)",
                       "formula1": "Fórmula 1", "motogp": "Motociclismo",
                       "horseracing": "Carreras de caballos"}

SPORT_LABELS_EN = {"soccer": "Soccer", "basketball": "Basketball", "tennis": "Tennis",
                       "americanfootball": "American football",
                       "boxing": "Boxing", "baseball": "Baseball",
                       "hockey": "Hockey (NHL)",
                       "formula1": "Formula 1", "motogp": "MotoGP",
                       "horseracing": "Horse racing"}

MODEL_LABELS = {
        "soccer": "Poisson de goles acoplado a ratings Elo",
        "basketball": "Elo con margen de localía (moneyline)",
        "tennis": "Elo de tenis (sin localía relevante)",
        "americanfootball": "Elo de fútbol americano con localía (moneyline)",
        "boxing": "Elo de boxeo en terreno neutral (sin localía)",
        "baseball": "Elo de béisbol con localía (moneyline)",
        "hockey": "Elo de hockey con localía (moneyline)",
        "formula1": "Elo de pilotos → Bradley-Terry (ganador de la carrera)",
        "motogp": "Elo de pilotos MotoGP → Bradley-Terry (ganador de la carrera)",
        "horseracing": "Elo de caballos → Bradley-Terry (ganador de la carrera)",
}

MODEL_LABELS_EN = {
        "soccer": "Goal-based Poisson model coupled with Elo ratings",
        "basketball": "Elo with home-court margin (moneyline)",
        "tennis": "Tennis Elo (no meaningful home edge)",
        "americanfootball": "American football Elo with home advantage (moneyline)",
        "boxing": "Boxing Elo on neutral ground (no home advantage)",
        "baseball": "Baseball Elo with home advantage (moneyline)",
        "hockey": "Hockey Elo with home advantage (moneyline)",
        "formula1": "Driver Elo → Bradley-Terry (race winner)",
        "motogp": "MotoGP rider Elo → Bradley-Terry (race winner)",
        "horseracing": "Horse Elo → Bradley-Terry (race winner)",
}

# Deportes sin ventaja de localía (circuito/pista/terreno neutral).
_SIN_LOCALIA = {"tennis", "boxing", "formula1", "motogp", "horseracing"}

# Ligas: los datos de demo vienen en español; en inglés se traducen aquí.
LEAGUE_EN = {
    "LaLiga · España": "LaLiga · Spain",
    "Liga MX · México": "Liga MX · Mexico",
    "MLB · Estados Unidos": "MLB · USA",
    "NBA · EE.UU.": "NBA · USA",
    "NFL · Estados Unidos": "NFL · USA",
    "NHL · EE.UU.": "NHL · USA",
    "Premier League · Inglaterra": "Premier League · England",
    "Boxeo · Campeonato peso pesado": "Boxing · Heavyweight title",
    "Boxeo · Evento principal": "Boxing · Main event",
    "Fórmula 1 · Gran Premio": "Formula 1 · Grand Prix",
    "Hípódromo · Carrera clásica": "Racecourse · Classic race",
    "MotoGP · Gran Premio": "MotoGP · Grand Prix",
    "ATP · Finals": "ATP · Finals",
    "WTA · Finals": "WTA · Finals",
}


def translate_league(name: str, lang: str) -> str:
    if lang == "en":
        return LEAGUE_EN.get(name, name)
    return name


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _step_model(rec: dict[str, Any], p_model: float, lang: str) -> str:
    """Paso 1: h2h (2 competidores) y outright (N participantes)."""
    sport = rec["sport"]
    model = MODEL_LABELS_EN[sport] if lang == "en" else MODEL_LABELS[sport]
    if lang == "en":
        if rec.get("market_type") == "outright":
            return (
                f"We use {model}: Elo ratings of the {rec.get('field_size', 0)} "
                f"entrants converted into probabilities with Bradley-Terry. "
                f"“{rec['selection_label']}” has a rating of {rec.get('elo_selection', 1500.0):.0f} "
                f"(field best {rec['elo_home']:.0f}, average {rec['elo_away']:.0f}) and the "
                f"model estimates a {_pct(p_model)} real chance of winning the race."
            )
        return (
            f"We use {model}: Elo ratings ({rec['elo_home']:.0f} vs "
            f"{rec['elo_away']:.0f}{' + home advantage' if sport not in _SIN_LOCALIA else ''}) "
            f"turn relative strength into a probability. For “{rec['selection_label']}” the "
            f"model estimates a {_pct(p_model)} real probability."
            + (f" Expected goals: {rec['model_detail']}" if rec.get("model_detail") else "")
        )
    if rec.get("market_type") == "outright":
        return (
            f"Usamos {model}: Elo de los {rec.get('field_size', 0)} "
            f"participantes convertido en probabilidades con Bradley-Terry. "
            f"«{rec['selection_label']}» tiene rating {rec.get('elo_selection', 1500.0):.0f} "
            f"(mejor del campo {rec['elo_home']:.0f}, media {rec['elo_away']:.0f}) y el "
            f"modelo le estima {_pct(p_model)} de probabilidad real de ganar la carrera."
        )
    return (
        f"Usamos {model}: los ratings Elo ({rec['elo_home']:.0f} vs "
        f"{rec['elo_away']:.0f}{' + localía' if sport not in _SIN_LOCALIA else ''}) convierten la "
        f"fuerza relativa en una probabilidad. Para «{rec['selection_label']}» el modelo "
        f"estima {_pct(p_model)} de probabilidad real."
        + (f" Goles esperados: {rec['model_detail']}" if rec.get("model_detail") else "")
    )


def build_explanation(rec: dict[str, Any], stats: dict[str, float],
                      n_backtest: int, lang: str = "es") -> dict[str, Any]:
    """Explicación estructurada: pasos, confianza y riesgos."""
    if lang not in SUPPORTED_LANGS:
        lang = "es"
    sport = rec["sport"]
    selection = rec["selection"]
    odds = rec["odds"]
    p_model = rec["model_prob"]
    p_market = rec["market_prob"]
    conf = rec["confidence"]
    ev = rec["ev"]
    edge = rec["edge"]
    kelly = rec.get("kelly", {})
    sport_label = SPORT_LABELS_EN[sport] if lang == "en" else SPORT_LABELS[sport]

    if lang == "en":
        steps = [
            {"title": "1. Our model",
             "detail": _step_model(rec, p_model, lang)},
            {"title": "2. What the market requires",
             "detail": (
                 f"Odds {odds:.2f} at {rec['bookmaker']} imply {_pct(rec['implied_prob'])} "
                 f"before commission. After removing the house margin ({_pct(rec['margin'])}, "
                 f"power method) the consensus market believes it happens {_pct(p_market)}.")},
            {"title": "3. Where the value is",
             "detail": (
                 f"The model sees {edge * 100:+.1f} percentage points more than the market. "
                 f"Expected value: EV = {_pct(p_model)} × {odds:.2f} − 1 = {ev * 100:+.1f}% per "
                 f"unit staked. Betting only when EV > 0 is the only mathematical way to expect "
                 f"long-term growth.")},
            {"title": "4. How much to bet (fractional Kelly)",
             "detail": (
                 f"Full Kelly: {_pct(kelly.get('kelly_full_pct', 0) / 100)}. We use "
                 f"{kelly.get('kelly_fraction_used', 0.25):.2f} × Kelly with a 3% bankroll cap → "
                 f"suggested stake {_pct(kelly.get('stake_pct', 0) / 100)} "
                 f"({kelly.get('stake_units', 0):.2f} units). This maximizes growth without "
                 f"risking the bankroll on normal variance.")},
            {"title": "5. When to bet",
             "detail": (
                 f"Before the start ({rec.get('commence_time', 'time to be confirmed')} UTC). "
                 f"Lines usually close worse for the best value: our history shows an average CLV "
                 f"of {stats.get('avg_clv_pct', 0):+.1f}%, meaning we enter better than the close "
                 f"on average — the most reliable predictor of profitability.")},
            {"title": "6. Why trust it (evidence)",
             "detail": (
                 f"Statistical confidence of {_pct(conf)} ≈ P(model > market), computed from the "
                 f"model's uncertainty (effective n = 60 matches) and the spread across bookmakers. "
                 f"In {n_backtest} historical {sport_label.lower()} picks the system recorded ROI "
                 f"{stats.get('roi_pct', 0):+.1f}%, hit rate {stats.get('hit_rate_pct', 0):.1f}% "
                 f"(breakeven {stats.get('breakeven_hit_pct', 0):.1f}%) and profit factor "
                 f"{stats.get('profit_factor', 0):.2f}."
                 + (_binomial_note(stats, "en") if n_backtest >= 20 else
                    " (Small sample so far: treat these figures as preliminary.)"))},
        ]
        risks = [
            "No model is always right: even with a 55% true probability, 45 out of 100 bets lose.",
            "Probabilities are estimates; injuries, absences or lineup changes are not always reflected.",
            "Only bet what you can afford to lose and respect the suggested stake (bankroll management).",
        ]
        if rec.get("market_type") == "outright":
            risks.insert(0, "Multi-entrant race: even the favourite usually sits below 50%, so variance "
                            "is high and long losing streaks are normal.")
        if edge < 0.05:
            risks.insert(0, "Narrow edge (<5 points): a small margin against the model's error.")
        summary = (
            f"“{rec['selection_label']}” at {odds:.2f} ({rec['bookmaker']}) offers "
            f"{ev * 100:+.1f}% expected value with {conf * 100:.0f}% confidence.")
        return {"summary": summary, "steps": steps, "risks": risks}

    steps = [
        {
            "title": "1. Nuestro modelo",
            "detail": _step_model(rec, p_model, "es"),
        },
        {
            "title": "2. Qué exige el mercado",
            "detail": (
                f"La cuota {odds:.2f} de {rec['bookmaker']} implica {_pct(rec['implied_prob'])} "
                f"antes de comisión. Tras eliminar el margen de la casa ({_pct(rec['margin'])}, "
                f"método de potencias) el mercado consensuado cree que ocurre {_pct(p_market)}."
            ),
        },
        {
            "title": "3. Dónde está el valor",
            "detail": (
                f"El modelo ve {edge * 100:+.1f} puntos porcentuales más que el mercado. "
                f"Valor esperado: EV = {_pct(p_model)} × {odds:.2f} − 1 = {ev * 100:+.1f}% por "
                f"unidad apostada. Apostar solo cuando EV > 0 es la única forma matemática de "
                f"esperar crecimiento a largo plazo."
            ),
        },
        {
            "title": "4. Cuánto apostar (Kelly fraccional)",
            "detail": (
                f"Kelly completo: {_pct(kelly.get('kelly_full_pct', 0) / 100)}. Usamos "
                f"{kelly.get('kelly_fraction_used', 0.25):.2f} × Kelly con tope de 3% del "
                f"bankroll → stake sugerido {_pct(kelly.get('stake_pct', 0) / 100)} "
                f"({kelly.get('stake_units', 0):.2f} unidades). Esto maximiza el crecimiento "
                f"sin arriesgar la banca en varianza normal."
            ),
        },
        {
            "title": "5. Cuándo apostar",
            "detail": (
                f"Antes del inicio ({rec.get('commence_time', 'horario por confirmar')} UTC). "
                f"Las líneas suelen cerrar peor para el mejor valor: nuestro histórico muestra "
                f"un CLV medio de {stats.get('avg_clv_pct', 0):+.1f}%, es decir, entramos "
                f"mejor que el cierre en promedio — el predictor más fiable de rentabilidad."
            ),
        },
        {
            "title": "6. Por qué confiar (evidencia)",
            "detail": (
                f"Confianza estadística de {_pct(conf)} ≈ P(modelo > mercado), calculada con la "
                f"incertidumbre del modelo (n_efectivo = 60 partidos) y la dispersión entre "
                f"casas. En {n_backtest} picks históricos de {sport_label.lower()} el "
                f"sistema registró ROI {stats.get('roi_pct', 0):+.1f}%, acierto "
                f"{stats.get('hit_rate_pct', 0):.1f}% (breakeven "
                f"{stats.get('breakeven_hit_pct', 0):.1f}%) y profit factor "
                f"{stats.get('profit_factor', 0):.2f}."
                + (_binomial_note(stats, "es") if n_backtest >= 20 else
                   " (muestra pequeña aún: trata estas cifras como preliminares.)")
            ),
        },
    ]

    risks = [
        "Ningún modelo acierta siempre: incluso con 55% de probabilidad real, 45 de cada 100 apuestas pierden.",
        "Las probabilidades son estimaciones; lesiones, bajas o cambios de alineación no siempre están reflejadas.",
        "Apuesta solo lo que puedas permitirte perder y respeta el stake sugerido (gestión de bankroll).",
    ]
    if rec.get("market_type") == "outright":
        risks.insert(0, "Carrera multi-participante: incluso el favorito suele quedar por debajo "
                        "del 50%, así que la varianza es alta y las rachas largas son normales.")
    if edge < 0.05:
        risks.insert(0, "Edge estrecho (<5 puntos): margen pequeño frente al error del modelo.")

    return {
        "summary": (
            f"«{rec['selection_label']}» a {odds:.2f} ({rec['bookmaker']}) ofrece "
            f"{ev * 100:+.1f}% de valor esperado con {conf * 100:.0f}% de confianza."
        ),
        "steps": steps,
        "risks": risks,
    }


def _binomial_note(stats: dict[str, float], lang: str = "es") -> str:
    p = stats.get("binomial_p_value", 1.0)
    if lang == "en":
        if p < 0.01:
            return (f" The binomial test gives p = {p:.4f} < 0.01: that hit rate is "
                    f"statistically incompatible with chance.")
        if p < 0.05:
            return (f" The binomial test gives p = {p:.3f} < 0.05: the edge is statistically "
                    f"significant at 95%.")
        return (f" The binomial test gives p = {p:.3f} ≥ 0.05: the edge is NOT yet statistically "
                f"significant — keep following the track record before raising stakes.")
    if p < 0.01:
        return (f" El test binomial da p = {p:.4f} < 0.01: esa tasa de aciertos es "
                f"estadísticamente incompatible con el azar.")
    if p < 0.05:
        return (f" El test binomial da p = {p:.3f} < 0.05: la ventaja es estadísticamente "
                f"significativa al 95%.")
    return (f" El test binomial da p = {p:.3f} ≥ 0.05: la ventaja aún NO es estadísticamente "
            f"significativa — sigue el track record antes de subir de stake.")


def performance_summary(history: list[dict], sport: str | None = None) -> dict:
    """Métricas de backtest a partir del historial guardado."""
    stakes = [h["stake_pct"] for h in history]
    profits = [h["profit"] for h in history]
    results = [h["won"] for h in history]
    odds = [h["odds"] for h in history]
    clv = [h["clv_pct"] for h in history]
    stats = bt.summarize(stakes, profits, results, odds, clv)
    stats["sport"] = sport or "all"
    stats["sample"] = len(history)
    # Gráfica de equity acumulada para el panel.
    equity, running = [], 0.0
    for p in profits:
        running += p
        equity.append(round(running, 3))
    stats["equity_curve"] = equity
    return stats
