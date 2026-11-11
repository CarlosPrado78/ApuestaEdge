"""Eliminación de la cuota (desvigado / remove-the-vig).

Toda cuota ofrecida por una casa de apuestas incluye un margen (vig).
Para comparar la probabilidad *real* que exige el mercado con la de
nuestro modelo hay que eliminar ese margen.
"""

from __future__ import annotations

import math
from typing import Sequence


def implied_probs(odds: Sequence[float]) -> list[float]:
    """Cuotas decimales -> probabilidades implícitas crudas (suman > 1)."""
    if any(o <= 1.0 for o in odds):
        raise ValueError(f"cuotas decimales inválidas: {list(odds)}")
    return [1.0 / o for o in odds]


def margin(odds: Sequence[float]) -> float:
    """Margen total de la casa (0.05 = 5%)."""
    return sum(implied_probs(odds)) - 1.0


def normalize(probs: Sequence[float]) -> list[float]:
    """Normalización proporcional (media de cuotas)."""
    total = sum(probs)
    if total <= 0:
        raise ValueError("probabilidades no positivas")
    return [p / total for p in probs]


def power(implied: Sequence[float], tol: float = 1e-12, max_iter: int = 200) -> list[float]:
    """Desvigado por método de potencias (Shin / power method).

    Busca el exponente ``k > 1`` tal que ``sum(p_i ** k) == 1``. A
    diferencia de la normalización proporcional, no castiga por igual a
    favoritos y claros perdedores: respeta mejor la estructura del
    mercado.
    """
    if len(implied) == 1:
        return [1.0]
    lo, hi = 1.0, 8.0
    # f(k) = sum(p^k) - 1 es estrictamente decreciente en k.
    for _ in range(max_iter):
        mid = (lo + hi) / 2.0
        f = sum(p ** mid for p in implied) - 1.0
        if abs(f) < tol:
            break
        if f > 0:
            lo = mid
        else:
            hi = mid
    else:
        mid = (lo + hi) / 2.0
    return [p ** mid for p in implied]


def remove_vig(odds: Sequence[float], method: str = "power") -> tuple[list[float], float]:
    """Devuelve ``(probabilidades_sin_vig, margen)`` para un mercado.

    ``method``: ``"power"`` (por defecto) o ``"proportional"``.
    """
    implied = implied_probs(odds)
    m = sum(implied) - 1.0
    if method == "proportional":
        probs = normalize(implied)
    elif method == "power":
        probs = power(implied)
    else:
        raise ValueError(f"método desconocido: {method}")
    return probs, m


def best_odds(odds_by_book: dict[str, float]) -> tuple[str, float]:
    """Mejor cuota decimal entre casas para una misma selección."""
    if not odds_by_book:
        raise ValueError("sin cuotas")
    book = max(odds_by_book, key=odds_by_book.get)
    return book, odds_by_book[book]


def clv_pct(opening: float, current: float) -> float:
    """Closing Line Value: ganancia relativa si la cuota bajó a nuestro favor.

    Ej.: entramos a 2.20 y cierra a 2.00 -> +10% de CLV (buen indicador
    de que conseguimos valor, independientemente del resultado).
    """
    if opening <= 1.0 or current <= 1.0:
        raise ValueError("cuotas inválidas")
    return (opening / current - 1.0) * 100.0


def kelly_stake_from_clv(opening: float, current: float) -> float:
    """Equivalente en bankroll del CLV (para documentación)."""
    return math.log(opening / current) if opening > current else 0.0
