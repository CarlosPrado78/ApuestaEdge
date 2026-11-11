"""Generación de explicaciones en lenguaje natural para cada recomendación.

Cada pick incluye el "por qué": qué modelo se usó, qué dice el mercado,
cuál es el valor esperado, por qué confiar (confianza estadística +
backtest con test binomial) y qué riesgos conlleva.
"""

from __future__ import annotations

from typing import Any

from .engine import backtest as bt

SPORT_LABELS = {"soccer": "Fútbol", "basketball": "Básquet", "tennis": "Tenis"}

MODEL_LABELS = {
    "soccer": "Poisson de goles acoplado a ratings Elo",
    "basketball": "Elo con margen de localía (moneyline)",
    "tennis": "Elo de tenis (sin localía relevante)",
}


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def build_explanation(rec: dict[str, Any], stats: dict[str, float],
                      n_backtest: int) -> dict[str, Any]:
    """Explicación estructurada: pasos, confianza y riesgos."""
    sport = rec["sport"]
    selection = rec["selection"]
    odds = rec["odds"]
    p_model = rec["model_prob"]
    p_market = rec["market_prob"]
    conf = rec["confidence"]
    ev = rec["ev"]
    edge = rec["edge"]
    kelly = rec.get("kelly", {})

    steps = [
        {
            "title": "1. Nuestro modelo",
            "detail": (
                f"Usamos {MODEL_LABELS[sport]}: los ratings Elo ({rec['elo_home']:.0f} vs "
                f"{rec['elo_away']:.0f}{' + localía' if sport != 'tennis' else ''}) convierten la "
                f"fuerza relativa en una probabilidad. Para «{rec['selection_label']}» el modelo "
                f"estima {_pct(p_model)} de probabilidad real."
                + (f" Goles esperados: {rec['model_detail']}" if rec.get("model_detail") else "")
            ),
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
                f"casas. En {n_backtest} picks históricos de {SPORT_LABELS[sport].lower()} el "
                f"sistema registró ROI {stats.get('roi_pct', 0):+.1f}%, acierto "
                f"{stats.get('hit_rate_pct', 0):.1f}% (breakeven "
                f"{stats.get('breakeven_hit_pct', 0):.1f}%) y profit factor "
                f"{stats.get('profit_factor', 0):.2f}."
                + (_binomial_note(stats) if n_backtest >= 20 else
                   " (muestra pequeña aún: trata estas cifras como preliminares.)")
            ),
        },
    ]

    risks = [
        "Ningún modelo acierta siempre: incluso con 55% de probabilidad real, 45 de cada 100 apuestas pierden.",
        "Las probabilidades son estimaciones; lesales, bajas o cambios de alineación no siempre están reflejadas.",
        "Apuesta solo lo que puedas permitirte perder y respeta el stake sugerido (gestión de bankroll).",
    ]
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


def _binomial_note(stats: dict[str, float]) -> str:
    p = stats.get("binomial_p_value", 1.0)
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
