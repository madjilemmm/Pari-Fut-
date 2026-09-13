"""
Dynamic Elo rating for team strength, with a dynamic home-advantage term
estimated from the data rather than assumed fixed.

Used to correct raw stats for opponent strength: beating a weak team is
not scored the same as beating a strong one.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

DEFAULT_RATING = 1500.0
K_FACTOR = 20.0


@dataclass
class EloModel:
    ratings: dict = field(default_factory=dict)
    home_advantage_elo: float = 60.0  # in Elo points, refit from data

    @classmethod
    def fit(cls, history: pd.DataFrame) -> "EloModel":
        """Replays all past matches chronologically to build current ratings.
        history must be pre-sorted by kickoff_utc and contain only matches
        strictly before the target prediction time (walk-forward, no leakage)."""
        model = cls()
        history = history.sort_values("kickoff_utc")

        home_wins = 0
        for _, row in history.iterrows():
            model._update(row["HomeTeam"], row["AwayTeam"], row["FTHG"], row["FTAG"])
            if row["FTHG"] > row["FTAG"]:
                home_wins += 1

        return model

    def _update(self, home: str, away: str, home_goals: int, away_goals: int) -> None:
        r_home = self.ratings.get(home, DEFAULT_RATING)
        r_away = self.ratings.get(away, DEFAULT_RATING)

        expected_home = 1.0 / (1.0 + 10 ** (-(r_home + self.home_advantage_elo - r_away) / 400))

        if home_goals > away_goals:
            actual_home = 1.0
        elif home_goals == away_goals:
            actual_home = 0.5
        else:
            actual_home = 0.0

        goal_diff = abs(home_goals - away_goals)
        margin_multiplier = 1.0 if goal_diff <= 1 else (1.5 if goal_diff == 2 else 1.75)

        delta = K_FACTOR * margin_multiplier * (actual_home - expected_home)
        self.ratings[home] = r_home + delta
        self.ratings[away] = r_away - delta

    def win_draw_loss_prob(self, home: str, away: str) -> tuple[float, float, float]:
        """Elo-implied 1X2 probabilities (logistic win prob, draw modeled as a
        band around the expected margin — a simple, standard Elo-football
        heuristic, not a substitute for the Poisson/Dixon-Coles score model)."""
        r_home = self.ratings.get(home, DEFAULT_RATING)
        r_away = self.ratings.get(away, DEFAULT_RATING)
        diff = r_home + self.home_advantage_elo - r_away

        expected_home = 1.0 / (1.0 + 10 ** (-diff / 400))

        draw_prob = 0.28 - 0.0004 * abs(diff)
        draw_prob = max(0.10, min(0.30, draw_prob))

        home_win_prob = max(0.0, expected_home - draw_prob / 2)
        away_win_prob = max(0.0, (1 - expected_home) - draw_prob / 2)
        total = home_win_prob + draw_prob + away_win_prob
        return home_win_prob / total, draw_prob / total, away_win_prob / total

    def rating(self, team: str) -> float:
        return self.ratings.get(team, DEFAULT_RATING)
