"""
Baseline Poisson model (independent home/away goals).

For a match to be predicted at time t, attack/defense strengths are fit using
ONLY matches with kickoff_utc < t (walk-forward, no leakage). This is the
project's baseline: every later model (Dixon-Coles, ML, ensemble) must beat
it out-of-sample before being kept.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product

import numpy as np
import pandas as pd
from scipy.stats import poisson

MAX_GOALS = 8


@dataclass
class PoissonModel:
    home_attack: dict
    home_defense: dict
    away_attack: dict
    away_defense: dict
    league_home_avg: float
    league_away_avg: float

    @classmethod
    def fit(cls, history: pd.DataFrame) -> "PoissonModel":
        """history: past matches only (FTHG, FTAG, HomeTeam, AwayTeam)."""
        teams = pd.unique(history[["HomeTeam", "AwayTeam"]].values.ravel())
        league_home_avg = history["FTHG"].mean()
        league_away_avg = history["FTAG"].mean()

        home_attack, home_defense, away_attack, away_defense = {}, {}, {}, {}
        for team in teams:
            home_games = history[history["HomeTeam"] == team]
            away_games = history[history["AwayTeam"] == team]

            home_attack[team] = _safe_ratio(home_games["FTHG"].mean(), league_home_avg)
            home_defense[team] = _safe_ratio(home_games["FTAG"].mean(), league_away_avg)
            away_attack[team] = _safe_ratio(away_games["FTAG"].mean(), league_away_avg)
            away_defense[team] = _safe_ratio(away_games["FTHG"].mean(), league_home_avg)

        return cls(home_attack, home_defense, away_attack, away_defense,
                   league_home_avg, league_away_avg)

    def expected_goals(self, home_team: str, away_team: str) -> tuple[float, float]:
        ha = self.home_attack.get(home_team, 1.0)
        hd = self.home_defense.get(home_team, 1.0)
        aa = self.away_attack.get(away_team, 1.0)
        ad = self.away_defense.get(away_team, 1.0)
        home_xg = self.league_home_avg * ha * ad
        away_xg = self.league_away_avg * aa * hd
        return float(home_xg), float(away_xg)

    def score_matrix(self, home_team: str, away_team: str) -> np.ndarray:
        home_xg, away_xg = self.expected_goals(home_team, away_team)
        home_probs = poisson.pmf(np.arange(MAX_GOALS + 1), home_xg)
        away_probs = poisson.pmf(np.arange(MAX_GOALS + 1), away_xg)
        return np.outer(home_probs, away_probs)

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

        scores = [
            (f"{i}-{j}", float(matrix[i, j]))
            for i, j in product(range(MAX_GOALS + 1), repeat=2)
        ]
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


def _safe_ratio(value: float, league_avg: float) -> float:
    if league_avg == 0 or pd.isna(value):
        return 1.0
    return float(value / league_avg)
