"""Backtesting: mide el rendimiento histórico del sistema.

Métricas que sostienen la confianza en las sugerencias:

- ROI / yield: beneficio por unidad apostada.
- Acierto y CLV (Closing Line Value): ¿ganamos a las casas aunque no
  acertemos? El CLV es el predictor de rentabilidad a largo plazo.
- Drawdown máximo y profit factor: riesgo y solidez.
- Test binomial: ¿la rentabilidad es estadísticamente significativa o
  cabría esperar por azar?
"""

from __future__ import annotations

import math
from typing import Sequence


def roi(stakes: Sequence[float], profits: Sequence[float]) -> float:
    """Beneficio total / capital apostado."""
    total_staked = sum(stakes)
    if total_staked <= 0:
        return 0.0
    return sum(profits) / total_staked


def yield_pct(stakes: Sequence[float], profits: Sequence[float]) -> float:
    """Alias en porcentaje del ROI por apuesta (yield)."""
    return roi(stakes, profits) * 100.0


def hit_rate(results: Sequence[int]) -> float:
    """Fracción de aciertos (1 = ganada, 0 = perdida)."""
    if not results:
        return 0.0
    return sum(1 for r in results if r) / len(results)


def max_drawdown(profits: Sequence[float]) -> float:
    """Máxima caída acumulada desde un máximo (en unidades)."""
    equity = peak = 0.0
    worst = 0.0
    for p in profits:
        equity += p
        peak = max(peak, equity)
        worst = min(worst, equity - peak)
    return abs(worst)


def profit_factor(profits: Sequence[float]) -> float:
    """Ganancias / pérdidas. > 1 = sistema rentable."""
    gains = sum(p for p in profits if p > 0)
    losses = -sum(p for p in profits if p < 0)
    if losses == 0:
        return float("inf") if gains > 0 else 0.0
    return gains / losses


def binomial_tail_probability(wins: int, trials: int, p0: float) -> float:
    """P(X >= wins) bajo H0: acertar al azar con probabilidad p0.

    Se usa p0 = 1/cuota_media (breakeven). p pequeño => la tasa de
    aciertos no se explica por azar.
    """
    if trials <= 0 or not 0.0 < p0 < 1.0:
        return 1.0
    return sum(math.comb(trials, k) * p0 ** k * (1 - p0) ** (trials - k)
               for k in range(wins, trials + 1))


def average_clv(clv_pct_values: Sequence[float]) -> float:
    """CLV medio en % (positivo = entramos mejor que el cierre)."""
    if not clv_pct_values:
        return 0.0
    return sum(clv_pct_values) / len(clv_pct_values)


def summarize(stakes: Sequence[float], profits: Sequence[float],
              results: Sequence[int], odds: Sequence[float],
              clv_pct_values: Sequence[float]) -> dict[str, float]:
    """Todas las métricas en un solo dict (para la API / panel)."""
    n = len(results)
    wins = sum(1 for r in results if r)
    avg_odds = sum(odds) / len(odds) if odds else 0.0
    p0 = 1.0 / avg_odds if avg_odds > 1.0 else 0.5
    return {
        "bets": n,
        "wins": wins,
        "hit_rate_pct": hit_rate(results) * 100.0,
        "roi_pct": yield_pct(stakes, profits),
        "profit_units": sum(profits),
        "avg_odds": avg_odds,
        "max_drawdown_units": max_drawdown(profits),
        "profit_factor": profit_factor(profits),
        "avg_clv_pct": average_clv(clv_pct_values),
        "binomial_p_value": binomial_tail_probability(wins, n, p0),
        "breakeven_hit_pct": p0 * 100.0,
    }
