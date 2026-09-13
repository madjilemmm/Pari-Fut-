"""Monte Carlo simulation engine: samples goal counts from the fitted
model's Poisson distributions (Dixon-Coles xG), rather than re-deriving
probabilities analytically. Used to cross-check the closed-form matrix and
to report simulation-based confidence intervals."""
from __future__ import annotations

import numpy as np

N_SIMULATIONS = 50_000


def simulate(home_xg: float, away_xg: float, n_simulations: int = N_SIMULATIONS, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    home_goals = rng.poisson(home_xg, n_simulations)
    away_goals = rng.poisson(away_xg, n_simulations)

    home_win = float(np.mean(home_goals > away_goals))
    draw = float(np.mean(home_goals == away_goals))
    away_win = float(np.mean(home_goals < away_goals))
    over_2_5 = float(np.mean((home_goals + away_goals) > 2.5))
    btts = float(np.mean((home_goals > 0) & (away_goals > 0)))

    return {
        "n_simulations": n_simulations,
        "home_win_prob": home_win,
        "draw_prob": draw,
        "away_win_prob": away_win,
        "over_2_5_prob": over_2_5,
        "btts_prob": btts,
        "mean_total_goals": float(np.mean(home_goals + away_goals)),
    }
