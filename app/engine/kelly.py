"""Criterio de Kelly: cuánto apostar.

    f* = (b·p - q) / b        b = cuota - 1, p = prob. modelo, q = 1 - p

``f* > 0`` solo si la apuesta tiene valor esperado positivo. El Kelly
exacto crece el bankroll a largo plazo pero es muy volátil, así que en
producción usamos **fracciones** (25% por defecto) y un tope por apuesta.
"""

from __future__ import annotations


def kelly_fraction(prob: float, decimal_odds: float) -> float:
    """Fracción óptima de Kelly (> 0 solo si hay valor)."""
    if not 0.0 <= prob <= 1.0:
        raise ValueError("probabilidad fuera de [0, 1]")
    if decimal_odds <= 1.0:
        raise ValueError("la cuota decimal debe ser > 1")
    b = decimal_odds - 1.0
    q = 1.0 - prob
    f = (b * prob - q) / b
    return max(f, 0.0)


def recommended_stake(prob: float, decimal_odds: float, bankroll: float,
                      fraction: float = 0.25, max_stake_pct: float = 0.03,
                      min_stake_pct: float = 0.005) -> dict[str, float]:
    """Stake recomendado con Kelly fraccional y tope de riesgo.

    - ``fraction``: fracción del Kelly (0.25 = un cuarto).
    - ``max_stake_pct``: tope duro (3% del bankroll por defecto).
    - ``min_stake_pct``: umbral mínimo para molestarse (0.5%).
    """
    if not 0 < fraction <= 1:
        raise ValueError("fraction debe estar en (0, 1]")
    full = kelly_fraction(prob, decimal_odds)
    scaled = full * fraction
    capped = min(scaled, max_stake_pct)
    stake_pct = 0.0 if capped < min_stake_pct else capped
    return {
        "kelly_full_pct": full * 100.0,
        "kelly_fraction_used": fraction,
        "stake_pct": stake_pct * 100.0,
        "stake_units": bankroll * stake_pct,
        "full_kelly_bet": full > 0,
    }
