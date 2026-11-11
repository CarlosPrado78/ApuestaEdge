"""Modelo de goles de Poisson acoplado a ratings Elo (fútbol).

Metodología (la usan la mayoría de modelos públicos serios):

1. Ratings Elo -> probabilidad de victoria local.
2. Esa probabilidad reparte el total esperado de goles entre local y
   visitante (más la ventaja de localía).
3. Cada equipo recibe una tasa ``lambda`` de goles Poisson.
4. La matriz de marcadores P(X=i, Y=j) = P(X=i)·P(Y=j) da las
   probabilidades de 1X2, más de 2.5 goles, ambos marcan, etc.

Se asume independencia entre los goles de cada equipo (aproximación
estándar; una mejora posible es Dixon-Coles para ajustar 0-0 y 1-1).
"""

from __future__ import annotations

import math

MAX_GOALS = 8  # truncamiento de la cola (error < 1e-6 en la práctica)


def poisson_pmf(lam: float, k: int) -> float:
    """P(X = k) para X ~ Poisson(lam)."""
    if lam < 0 or k < 0:
        raise ValueError("lambda y k deben ser >= 0")
    return math.exp(-lam) * lam ** k / math.factorial(k)


def expected_score(lambda_home: float, lambda_away: float,
                   max_goals: int = MAX_GOALS) -> float:
    """P(victoria) + 0.5·P(empate): equivalente al 'score' esperado del Elo."""
    matrix = score_matrix(lambda_home, lambda_away, max_goals)
    mass = sum(p for row in matrix for p in row)  # < 1 por el truncamiento
    win = draw = 0.0
    for i, row in enumerate(matrix):
        for j, p in enumerate(row):
            if i > j:
                win += p
            elif i == j:
                draw += p
    return (win + 0.5 * draw) / mass


def expected_lambdas(elo_home: float, elo_away: float,
                     base_total: float = 2.65,
                     home_advantage: float = 60.0) -> tuple[float, float]:
    """Convierte los ratings Elo en tasas de goles **calibradas**.

    1. Elo -> 'score' esperado P(victoria) + 0.5·P(empate).
    2. Se busca el reparto de goles (local/visitante) cuya matriz de
       Poisson reproduce ese score. Así el modelo no se desvía
       sistemáticamente del mercado: las probabilidades 1X2 quedan
       calibradas con la fuerza real de los equipos.

    ``base_total``: media de goles de la liga (fútbol de élite ~2.6-2.8).
    """
    if base_total <= 0:
        raise ValueError("base_total debe ser > 0")
    # La localía suma al LOCAL: diferencia efectiva = (away − home − ventaja).
    target = 1.0 / (1.0 + 10 ** ((elo_away - home_advantage - elo_home) / 400.0))
    lo, hi = 0.10, 0.90
    for _ in range(40):  # E(share) es creciente -> búsqueda binaria estable
        mid = (lo + hi) / 2.0
        e = expected_score(base_total * mid, base_total * (1.0 - mid))
        if e < target:
            lo = mid
        else:
            hi = mid
    share = (lo + hi) / 2.0
    return base_total * share, base_total * (1.0 - share)


def score_matrix(lambda_home: float, lambda_away: float,
                 max_goals: int = MAX_GOALS) -> list[list[float]]:
    """Matriz P(local = i, visitante = j)."""
    ph = [poisson_pmf(lambda_home, i) for i in range(max_goals + 1)]
    pa = [poisson_pmf(lambda_away, j) for j in range(max_goals + 1)]
    return [[ph[i] * pa[j] for j in range(max_goals + 1)]
            for i in range(max_goals + 1)]


def match_probabilities(lambda_home: float, lambda_away: float,
                        max_goals: int = MAX_GOALS) -> dict[str, float]:
    """Probabilidades del mercado 1X2, líneas de goles y ambos marcan."""
    matrix = score_matrix(lambda_home, lambda_away, max_goals)
    p_home = p_draw = p_away = p_btts = p_over25 = 0.0
    p_over15 = p_over35 = 0.0
    for i, row in enumerate(matrix):
        for j, p in enumerate(row):
            if i > j:
                p_home += p
            elif i == j:
                p_draw += p
            else:
                p_away += p
            if i > 0 and j > 0:
                p_btts += p
            total = i + j
            if total >= 2:
                p_over15 += p
            if total >= 3:
                p_over25 += p
            if total >= 4:
                p_over35 += p
    normalizer = p_home + p_draw + p_away  # ~1 por el truncamiento
    return {
        "home": p_home / normalizer,
        "draw": p_draw / normalizer,
        "away": p_away / normalizer,
        "btts": p_btts / normalizer,
        "over_1_5": p_over15 / normalizer,
        "over_2_5": p_over25 / normalizer,
        "over_3_5": p_over35 / normalizer,
        "lambda_home": lambda_home,
        "lambda_away": lambda_away,
    }


def most_likely_score(lambda_home: float, lambda_away: float,
                      max_goals: int = MAX_GOALS) -> tuple[int, int, float]:
    """Marcador más probable (para explicar la recomendación)."""
    best = (0, 0, 0.0)
    for i, row in enumerate(score_matrix(lambda_home, lambda_away, max_goals)):
        for j, p in enumerate(row):
            if p > best[2]:
                best = (i, j, p)
    return best
