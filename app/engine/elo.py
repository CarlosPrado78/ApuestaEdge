"""Ratings Elo multi-deporte con ventaja de localía.

El Elo es el estándar de facto para estimar la fuerza relativa de dos
competidores a partir de resultados históricos. La probabilidad esperada
de victoria se deriva de la diferencia de ratings con la función logística:

    P(A gana) = 1 / (1 + 10 ** ((R_B - R_A) / 400))
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EloConfig:
    k: float = 24.0                 # sensibilidad del update por partido
    home_advantage: float = 60.0    # puntos equivalentes de jugar en casa
    base_rating: float = 1500.0


class EloRatings:
    """Contenedor de ratings + cálculo de expectativas y actualizaciones."""

    def __init__(self, ratings: dict[str, float] | None = None,
                 config: EloConfig | None = None) -> None:
        self.config = config or EloConfig()
        self.ratings: dict[str, float] = dict(ratings or {})

    def rating(self, team: str) -> float:
        return self.ratings.get(team, self.config.base_rating)

    def expected(self, home: str, away: str) -> float:
        """Probabilidad de victoria local (0.5 = moneda al aire).

        La localía suma ``home_advantage`` puntos al rating del LOCAL.
        """
        ra = self.rating(home) + self.config.home_advantage
        rb = self.rating(away)
        return 1.0 / (1.0 + 10 ** ((rb - ra) / 400.0))

    @staticmethod
    def outcome(home_score: float, away_score: float) -> float:
        """Resultado observado: 1 victoria local, 0.5 empate, 0 derrota."""
        if home_score > away_score:
            return 1.0
        if home_score < away_score:
            return 0.0
        return 0.5

    @staticmethod
    def margin_multiplier(goal_diff: int) -> float:
        """Multiplicador por diferencia de goles (convención clásica)."""
        d = abs(goal_diff)
        if d <= 1:
            return 1.0
        if d == 2:
            return 1.5
        return (11.0 + d) / 8.0

    def update(self, home: str, away: str, home_score: float,
               away_score: float) -> None:
        """Actualiza ambos ratings tras un partido (también sirve para
        básquet/tenis usando el resultado directo)."""
        p_home = self.expected(home, away)
        s_home = self.outcome(home_score, away_score)
        diff = home_score - away_score
        mult = self.margin_multiplier(int(diff)) if diff else 1.0
        delta = self.config.k * mult * (s_home - p_home)
        self.ratings[home] = self.rating(home) + delta
        self.ratings[away] = self.rating(away) - delta
