"""
Shots-on-target Poisson model, used to blend with DixonColesModel's
goals-based prediction.

Rationale, validated in ml/evaluation/shots_based_experiment.py: goals are
noisy (a team can dominate on chances and still lose 0-1), so estimating
team strength from shots on target (HST/AST — already in our raw data)
gives a lower-variance signal than goals alone. Blending it with the
goals-based model, at a weight chosen on a held-out VALIDATION season
(2022-2023) and verified unchanged on the TEST season (2023-2025), reduced
Log Loss from 0.9577 (goals alone) to 0.9540 — a real, modest improvement,
still short of the market (0.9330). Never claimed as more than that.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import gammaln
from scipy.stats import poisson

MAX_SHOTS_GOALS = 8

# Found by ml/evaluation/shots_based_experiment.py: the weight minimizing
# Log Loss on the 2022-2023 validation season, applied unchanged to the
# 2023-2025 test season (LogLoss 0.9540 vs 0.9577 goals-only, 0.9330 market).
SHOTS_BLEND_WEIGHT = 0.836


@dataclass
class ShotsModel:
    attack: dict
    defense: dict
    home_advantage: float
    home_conversion_rate: float
    away_conversion_rate: float

    @classmethod
    def fit(cls, history: pd.DataFrame, xi: float = 0.005) -> "ShotsModel | None":
        """Returns None when history lacks usable HST/AST data (e.g. too few
        rows) rather than fitting on a degenerate sample."""
        usable = history.dropna(subset=["HST", "AST"])
        if len(usable) < 50:
            return None

        teams = sorted(pd.unique(usable[["HomeTeam", "AwayTeam"]].values.ravel()))
        n = len(teams)
        idx = {t: i for i, t in enumerate(teams)}

        max_date = usable["kickoff_utc"].max()
        days_ago = (max_date - usable["kickoff_utc"]).dt.total_seconds() / 86400.0
        weights = np.exp(-xi * days_ago.values)

        home_idx = usable["HomeTeam"].map(idx).values
        away_idx = usable["AwayTeam"].map(idx).values
        h = usable["HST"].values
        a = usable["AST"].values

        x0 = np.concatenate([np.zeros(n), np.zeros(n), [0.1]])

        def neg_log_likelihood(params):
            attack = params[:n]
            defense = params[n:2 * n]
            home_adv = params[2 * n]
            lam = np.exp(attack[home_idx] + defense[away_idx] + home_adv)
            mu = np.exp(attack[away_idx] + defense[home_idx])
            ll = (h * np.log(lam) - lam - gammaln(h + 1)) + (a * np.log(mu) - mu - gammaln(a + 1))
            penalty = 1000 * (attack.mean()) ** 2
            return -np.sum(weights * ll) + penalty

        result = minimize(neg_log_likelihood, x0, method="L-BFGS-B", options={"ftol": 1e-6, "gtol": 1e-4})
        params = result.x
        attack = dict(zip(teams, params[:n]))
        defense = dict(zip(teams, params[n:2 * n]))
        home_adv = float(params[2 * n])

        # Conversion rate (goals per shot on target) computed only from this
        # same history slice — never leaks future data.
        home_conv = float(history["FTHG"].sum() / usable["HST"].sum()) if usable["HST"].sum() > 0 else 0.0
        away_conv = float(history["FTAG"].sum() / usable["AST"].sum()) if usable["AST"].sum() > 0 else 0.0

        return cls(attack, defense, home_adv, home_conv, away_conv)

    def predict_outcome(self, home_team: str, away_team: str) -> tuple[float, float, float] | None:
        """Returns (home_win, draw, away_win) or None if either team has no
        fitted shots-based rating (e.g. promoted club, thin history)."""
        if home_team not in self.attack or away_team not in self.attack:
            return None
        if self.home_conversion_rate <= 0 or self.away_conversion_rate <= 0:
            return None

        home_xsot = float(np.exp(self.attack[home_team] + self.defense[away_team] + self.home_advantage))
        away_xsot = float(np.exp(self.attack[away_team] + self.defense[home_team]))
        home_xg = home_xsot * self.home_conversion_rate
        away_xg = away_xsot * self.away_conversion_rate

        home_probs = poisson.pmf(np.arange(MAX_SHOTS_GOALS + 1), home_xg)
        away_probs = poisson.pmf(np.arange(MAX_SHOTS_GOALS + 1), away_xg)
        matrix = np.outer(home_probs, away_probs)
        matrix /= matrix.sum()

        home_win = float(np.tril(matrix, -1).sum())
        draw = float(np.trace(matrix))
        away_win = float(np.triu(matrix, 1).sum())
        return home_win, draw, away_win


def blend_with_goals(
    goals_probs: tuple[float, float, float],
    shots_probs: tuple[float, float, float] | None,
    weight: float = SHOTS_BLEND_WEIGHT,
) -> tuple[float, float, float]:
    """Blends goals-based and shots-based outcome probabilities. Falls back
    to goals_probs unchanged when shots_probs is unavailable — never
    fabricates a shots-based estimate for a team with no shots history."""
    if shots_probs is None:
        return goals_probs
    gh, gd, ga = goals_probs
    sh, sd, sa = shots_probs
    bh = weight * sh + (1 - weight) * gh
    bd = weight * sd + (1 - weight) * gd
    ba = weight * sa + (1 - weight) * ga
    total = bh + bd + ba
    return bh / total, bd / total, ba / total
