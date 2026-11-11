"""Tests del motor estadístico (devig, Poisson, Elo, Kelly, EV, backtest)."""

import math

import pytest

from app.engine import backtest as bt
from app.engine import devig, elo as elo_mod, ev, kelly, poisson


# ---------------------------------------------------------------- devig
def test_implied_probs_sum_more_than_one():
    probs = devig.implied_probs([2.0, 3.5, 4.0])
    assert sum(probs) == pytest.approx(1.0357, abs=1e-4)  # > 1: ahí vive el margen


def test_power_devig_returns_true_probabilities():
    probs, m = devig.remove_vig([1.95, 3.75, 4.00], method="power")
    assert sum(probs) == pytest.approx(1.0, abs=1e-6)
    assert m == pytest.approx(0.0295, abs=5e-3)
    # El método de potencias pondera mejor al favorito que lo simple.
    prop, _ = devig.remove_vig([1.95, 3.75, 4.00], method="proportional")
    assert probs[0] > prop[0]  # el favorito conserva más probabilidad


def test_margin_and_best_odds():
    assert devig.margin([2.0, 2.0]) == pytest.approx(0.0)
    book, odds = devig.best_odds({"a": 1.9, "b": 2.1, "c": 2.0})
    assert (book, odds) == ("b", 2.1)


def test_clv_positive_when_we_enter_better():
    assert devig.clv_pct(2.20, 2.00) == pytest.approx(10.0)
    with pytest.raises(ValueError):
        devig.clv_pct(0.0, 2.0)


def test_invalid_odds_rejected():
    with pytest.raises(ValueError):
        devig.implied_probs([0.9, 2.0])
    with pytest.raises(ValueError):
        devig.remove_vig([2.0, 3.0], method="nope")


# ---------------------------------------------------------------- Poisson
def test_poisson_pmf():
    assert poisson.poisson_pmf(1.5, 0) == pytest.approx(math.exp(-1.5))
    # P(X=2) con λ=2: e^-2 · 2^2 / 2! = 2·e^-2
    assert poisson.poisson_pmf(2.0, 2) == pytest.approx(2.0 * math.exp(-2.0))


def test_match_probabilities_are_a_distribution():
    p = poisson.match_probabilities(1.6, 1.1)
    assert p["home"] + p["draw"] + p["away"] == pytest.approx(1.0, abs=1e-6)
    assert 0.0 < p["draw"] < 0.4
    assert p["over_1_5"] >= p["over_2_5"] >= p["over_3_5"]
    assert 0.0 < p["over_2_5"] < 1.0


def test_lambdas_are_calibrated_to_elo_score():
    """Las tasas Poisson deben reproducir el score esperado del Elo."""
    for elo_h, elo_a in [(1980, 1970), (1500, 1500), (1700, 2050)]:
        lam_h, lam_a = poisson.expected_lambdas(elo_h, elo_a)
        target = 1.0 / (1.0 + 10 ** ((elo_a - 60 - elo_h) / 400.0))
        assert poisson.expected_score(lam_h, lam_a) == pytest.approx(target, abs=5e-3)


def test_unequal_teams_produce_unequal_lambdas():
    lam_h, lam_a = poisson.expected_lambdas(2100, 1700)
    assert lam_h > lam_a


def test_most_likely_score():
    i, j, p = poisson.most_likely_score(1.4, 1.1)
    assert i >= 0 and j >= 0 and 0 < p < 0.3


# ---------------------------------------------------------------- Elo
def test_elo_expected_is_symmetric_and_neutral():
    r = elo_mod.EloRatings({"A": 1500, "B": 1500}, config=elo_mod.EloConfig(home_advantage=0))
    assert r.expected("A", "B") == pytest.approx(0.5)
    r2 = elo_mod.EloRatings({"A": 1700, "B": 1500}, config=elo_mod.EloConfig(home_advantage=0))
    assert r2.expected("A", "B") > 0.5


def test_elo_home_advantage_helps_home():
    r = elo_mod.EloRatings({"A": 1500, "B": 1500})
    assert r.expected("A", "B") > 0.5


def test_elo_update_moves_ratings_toward_result():
    r = elo_mod.EloRatings({"A": 1500, "B": 1500})
    before_home, before_away = r.rating("A"), r.rating("B")
    r.update("A", "B", home_score=3, away_score=0)
    assert r.rating("A") > before_home
    assert r.rating("B") < before_away
    # Un resultado abultado mueve más que uno ajustado.
    r2 = elo_mod.EloRatings({"A": 1500, "B": 1500})
    r2.update("A", "B", home_score=1, away_score=0)
    assert r.rating("A") - before_home > r2.rating("A") - before_home


# ---------------------------------------------------------------- Kelly
def test_kelly_positive_only_with_value():
    # Cuota 2.00, prob real 0.60 -> valor.
    assert kelly.kelly_fraction(0.60, 2.0) > 0
    # Cuota 2.00, prob 0.45 -> sin valor: Kelly = 0.
    assert kelly.kelly_fraction(0.45, 2.0) == 0.0


def test_kelly_exact_value():
    # f* = (b·p − q)/b = (1×0.6 − 0.4)/1 = 0.2
    assert kelly.kelly_fraction(0.6, 2.0) == pytest.approx(0.2)


def test_stake_is_fractional_and_capped():
    s = kelly.recommended_stake(0.6, 2.0, bankroll=1000, fraction=0.25,
                                max_stake_pct=0.03)
    assert s["kelly_full_pct"] == pytest.approx(20.0)
    assert s["stake_pct"] == pytest.approx(3.0)  # tope 3% pese a 0.25×20=5%
    assert s["stake_units"] == pytest.approx(30.0)
    s2 = kelly.recommended_stake(0.6, 2.0, bankroll=1000, fraction=0.25,
                                 max_stake_pct=0.05, min_stake_pct=0.005)
    assert s2["stake_pct"] == pytest.approx(5.0)  # 0.25×20% = 5%
    assert s2["full_kelly_bet"] is True


def test_kelly_rejects_bad_inputs():
    with pytest.raises(ValueError):
        kelly.kelly_fraction(1.2, 2.0)
    with pytest.raises(ValueError):
        kelly.kelly_fraction(0.5, 1.0)


# ---------------------------------------------------------------- EV / confianza
def test_expected_value_sign():
    assert ev.expected_value(0.55, 2.0) == pytest.approx(0.10)
    assert ev.expected_value(0.40, 2.0) == pytest.approx(-0.20)


def test_confidence_monotonic_in_edge():
    books = [0.47, 0.48, 0.475]
    low = ev.confidence(0.50, 0.47, books)
    high = ev.confidence(0.60, 0.47, books)
    assert 0.5 < low < high < 1.0


def test_market_sigma_reflects_book_disagreement():
    tight = ev.market_sigma([0.47, 0.471, 0.469])
    wide = ev.market_sigma([0.40, 0.50, 0.60])
    assert tight < wide
    assert ev.market_sigma([0.47]) == pytest.approx(0.02)  # sin consenso


def test_bayesian_interval_contains_mean():
    lo, hi = ev.bayesian_win_interval(60, 100)
    assert lo < 0.60 < hi


# ---------------------------------------------------------------- Backtest
def test_roi_and_drawdown():
    stakes = [1.0, 1.0, 1.0]
    profits = [1.0, -1.0, -1.0]
    assert bt.roi(stakes, profits) == pytest.approx(-1.0 / 3.0)
    assert bt.max_drawdown([1.0, -1.0, -1.0]) == pytest.approx(2.0)


def test_profit_factor():
    assert bt.profit_factor([2.0, -1.0]) == pytest.approx(2.0)


def test_binomial_tail():
    # Con p0=0.5, acertar 10/10 es prácticamente imposible.
    assert bt.binomial_tail_probability(10, 10, 0.5) == pytest.approx(1 / 1024)
    assert bt.binomial_tail_probability(0, 10, 0.5) == pytest.approx(1.0)


def test_summarize_structure():
    stats = bt.summarize([1.0] * 10, [1.0, -1.0] * 5, [1, 0] * 5,
                         [2.0] * 10, [3.0] * 10)
    assert stats["bets"] == 10
    assert stats["wins"] == 5
    assert stats["hit_rate_pct"] == pytest.approx(50.0)
    assert stats["avg_clv_pct"] == pytest.approx(3.0)
    assert 0.0 <= stats["binomial_p_value"] <= 1.0
