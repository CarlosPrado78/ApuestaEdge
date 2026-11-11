"""Valor esperado, edge y confianza estadística.

- ``edge``: diferencia entre la probabilidad del modelo y la del mercado
  ya desvigado (nuestra ventaja estimada).
- ``ev``: ganancia esperada por unidad apostada con la cuota dada.
- ``confidence``: P(modelo > mercado) bajo aproximación normal
  (distribución posterior del modelo con un tamaño muestral efectivo,
  combinado con la dispersión entre casas de apuestas).
"""

from __future__ import annotations

import math

# Tamaño muestral efectivo de los ratings (partidos ponderados usados
# para estimar la probabilidad del modelo). Más partidos -> menor sigma.
DEFAULT_EFFECTIVE_N = 60


def expected_value(prob: float, decimal_odds: float) -> float:
    """EV por unidad: p·cuota - 1. EV > 0 = valor esperado positivo."""
    if decimal_odds <= 1.0:
        raise ValueError("la cuota decimal debe ser > 1")
    return prob * decimal_odds - 1.0


def edge(prob_model: float, prob_market: float) -> float:
    """Edge lineal (prob_modelo - prob_mercado)."""
    return prob_model - prob_market


def profit_ratio(prob: float, decimal_odds: float) -> float:
    """Retorno relativo esperado (EV / stake)."""
    return expected_value(prob, decimal_odds)


def normal_cdf(z: float) -> float:
    """Phi(z) con aproximación de erf (stdlib, sin dependencias)."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def model_sigma(prob: float, n_eff: int = DEFAULT_EFFECTIVE_N) -> float:
    """Incertidumbre de la probabilidad del modelo (binomial efectiva)."""
    if n_eff < 2:
        raise ValueError("n_eff debe ser >= 2")
    p = min(max(prob, 1e-6), 1 - 1e-6)
    return math.sqrt(p * (1.0 - p) / n_eff)


def market_sigma(probs_by_book: list[float]) -> float:
    """Dispersión de las probabilidades sin vig entre casas."""
    if len(probs_by_book) < 2:
        return 0.02  # sin consenso: asumimos cierta incertidumbre
    n = len(probs_by_book)
    mean = sum(probs_by_book) / n
    var = sum((p - mean) ** 2 for p in probs_by_book) / (n - 1)
    return max(math.sqrt(var), 0.005)


def confidence(prob_model: float, prob_market: float,
               probs_by_book: list[float],
               n_eff: int = DEFAULT_EFFECTIVE_N) -> float:
    """P(modelo > mercado) en [0, 1] con aproximación normal.

    z = (p_model - p_market) / sqrt(sigma_model^2 + sigma_market^2)
    confianza = Phi(z)
    """
    sigma = math.hypot(model_sigma(prob_model, n_eff),
                       market_sigma(probs_by_book))
    z = (prob_model - prob_market) / sigma
    return normal_cdf(z)


def bayesian_win_interval(wins: int, trials: int, z: float = 1.96,
                          prior_alpha: float = 1.0,
                          prior_beta: float = 1.0) -> tuple[float, float]:
    """IC ~95% (aprox. normal) para la tasa de acierto observada.

    Prior Beta(1,1) (uniforme) -> posterior Beta(wins+a, losses+b).
    """
    if trials < 0 or wins < 0 or wins > trials:
        raise ValueError("conteos inválidos")
    a = wins + prior_alpha
    b = trials - wins + prior_beta
    n = a + b
    mean = a / n
    var = (a * b) / (n ** 2 * (n + 1.0))
    sigma = math.sqrt(var)
    return max(mean - z * sigma, 0.0), min(mean + z * sigma, 1.0)
