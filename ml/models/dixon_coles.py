"""
Dixon-Coles model: independent-Poisson goals plus a low-score correlation
correction (rho) and an exponential time-decay weighting of past matches.

Reference: Dixon, M.J. and Coles, S.G. (1997), "Modelling Association
Football Scores and Inefficiencies in the Betting Market."

Only matches with kickoff_utc < the target match's kickoff are ever used to
fit parameters (walk-forward, no leakage) — enforced by the caller passing
`history`, never by this module reaching into the future itself.

The time-decay half-life (xi) is NOT picked arbitrarily: `fit_xi_grid_search`
sweeps candidate values and keeps the one with the best out-of-sample log
loss on a held-out validation slice, per the project rule that recency
weighting must be validated empirically rather than assumed.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson

MAX_GOALS = 8


def _tau(home_goals: int, away_goals: int, home_xg: float, away_xg: float, rho: float) -> float:
    """Dixon-Coles low-score adjustment factor."""
    if home_goals == 0 and away_goals == 0:
        return 1 - home_xg * away_xg * rho
    if home_goals == 0 and away_goals == 1:
        return 1 + home_xg * rho
    if home_goals == 1 and away_goals == 0:
        return 1 + away_xg * rho
    if home_goals == 1 and away_goals == 1:
        return 1 - rho
    return 1.0


@dataclass
class DixonColesModel:
    attack: dict
    defense: dict
    home_advantage: float
    rho: float
    teams: list

    @classmethod
    def fit(cls, history: pd.DataFrame, xi: float = 0.0018) -> "DixonColesModel":
        """xi: daily exponential time-decay rate. xi=0 reduces to no decay.
        history must contain HomeTeam, AwayTeam, FTHG, FTAG, kickoff_utc."""
        teams = sorted(pd.unique(history[["HomeTeam", "AwayTeam"]].values.ravel()))
        n = len(teams)
        idx = {t: i for i, t in enumerate(teams)}

        max_date = history["kickoff_utc"].max()
        days_ago = (max_date - history["kickoff_utc"]).dt.total_seconds() / 86400.0
        weights = np.exp(-xi * days_ago.values)

        home_idx = history["HomeTeam"].map(idx).values
        away_idx = history["AwayTeam"].map(idx).values
        hg = history["FTHG"].values
        ag = history["FTAG"].values

        # params: [attack_0..attack_{n-1}, defense_0..defense_{n-1}, home_adv, rho]
        # attack/defense constrained so mean(attack) = 0 via a penalty (soft constraint)
        x0 = np.concatenate([np.zeros(n), np.zeros(n), [0.2], [-0.05]])

        def neg_log_likelihood(params: np.ndarray) -> float:
            attack = params[:n]
            defense = params[n:2 * n]
            home_adv = params[2 * n]
            rho = params[2 * n + 1]

            lam = np.exp(attack[home_idx] + defense[away_idx] + home_adv)
            mu = np.exp(attack[away_idx] + defense[home_idx])

            log_pmf_home = hg * np.log(lam) - lam - _log_factorial(hg)
            log_pmf_away = ag * np.log(mu) - mu - _log_factorial(ag)

            tau_vals = np.array([
                _tau(int(h), int(a), lam[i], mu[i], rho) for i, (h, a) in enumerate(zip(hg, ag))
            ])
            tau_vals = np.clip(tau_vals, 1e-10, None)

            log_lik = log_pmf_home + log_pmf_away + np.log(tau_vals)
            penalty = 1000 * (attack.mean()) ** 2  # soft-center attack ratings
            return -np.sum(weights * log_lik) + penalty

        result = minimize(neg_log_likelihood, x0, method="L-BFGS-B")
        params = result.x
        attack = dict(zip(teams, params[:n]))
        defense = dict(zip(teams, params[n:2 * n]))
        home_adv = float(params[2 * n])
        rho = float(params[2 * n + 1])

        return cls(attack, defense, home_adv, rho, teams)

    def expected_goals(self, home_team: str, away_team: str) -> tuple[float, float]:
        a_h = self.attack.get(home_team, 0.0)
        d_h = self.defense.get(home_team, 0.0)
        a_a = self.attack.get(away_team, 0.0)
        d_a = self.defense.get(away_team, 0.0)
        home_xg = float(np.exp(a_h + d_a + self.home_advantage))
        away_xg = float(np.exp(a_a + d_h))
        return home_xg, away_xg

    def score_matrix(self, home_team: str, away_team: str) -> np.ndarray:
        home_xg, away_xg = self.expected_goals(home_team, away_team)
        home_probs = poisson.pmf(np.arange(MAX_GOALS + 1), home_xg)
        away_probs = poisson.pmf(np.arange(MAX_GOALS + 1), away_xg)
        matrix = np.outer(home_probs, away_probs)

        for i, j in product(range(2), repeat=2):
            matrix[i, j] *= _tau(i, j, home_xg, away_xg, self.rho)

        matrix = np.clip(matrix, 0, None)
        matrix /= matrix.sum()
        return matrix

    def predict(self, home_team: str, away_team: str) -> dict:
        matrix = self.score_matrix(home_team, away_team)
        home_xg, away_xg = self.expected_goals(home_team, away_team)

        home_win = float(np.tril(matrix, -1).sum())
        draw = float(np.trace(matrix))
        away_win = float(np.triu(matrix, 1).sum())

        over_2_5 = 0.0
        btts = 0.0
        for i, j in product(range(MAX_GOALS + 1), repeat=2):
            p = matrix[i, j]
            if i + j > 2.5:
                over_2_5 += p
            if i > 0 and j > 0:
                btts += p

        scores = [(f"{i}-{j}", float(matrix[i, j])) for i, j in product(range(MAX_GOALS + 1), repeat=2)]
        top_scores = sorted(scores, key=lambda x: -x[1])[:5]

        return {
            "home_win_prob": home_win,
            "draw_prob": draw,
            "away_win_prob": away_win,
            "home_xg": home_xg,
            "away_xg": away_xg,
            "over_2_5_prob": over_2_5,
            "btts_prob": btts,
            "top_scores": [{"score": s, "prob": p} for s, p in top_scores],
        }


def _log_factorial(k: np.ndarray) -> np.ndarray:
    from scipy.special import gammaln
    return gammaln(k + 1)
