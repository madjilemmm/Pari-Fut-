"""
Honest attempt at an independent edge over the market: goals are noisy (a
team can dominate on shots and still lose 0-1), so a model of TRUE team
strength based on shots-on-target (HST/AST columns, already in our raw
CSVs) might separate signal from luck better than goals alone — this is a
well-documented idea in football analytics (shots/xG models tend to be
more stable than goals models over small samples).

Method, same walk-forward + train/validation/test discipline as everywhere
else in this project:
1. Fit a Poisson attack/defense model on shots-on-target instead of goals
   (identical MLE machinery to DixonColesModel.fit, different response).
2. Convert predicted shots-on-target to an expected-goals estimate using a
   goals-per-shot-on-target conversion rate computed ONLY from history
   strictly before the target match (walk-forward, no leakage).
3. Blend this shots-based xG estimate with the existing goals-based
   Dixon-Coles model (simple average of the two independent-Poisson score
   matrices), weight chosen on the VALIDATION season (2022-2023) only.
4. Apply that weight unchanged to the TEST season (2023-2025) and report
   the result honestly, whatever it is.
"""
from __future__ import annotations

import glob
import os
from itertools import product

import numpy as np
import pandas as pd
from scipy.optimize import minimize, minimize_scalar
from scipy.special import gammaln
from scipy.stats import poisson
from sklearn.metrics import log_loss

from ml.models.dixon_coles import DixonColesModel, MAX_GOALS

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw")
PROCESSED_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed", "matches.parquet")


def fit_poisson_rates(history: pd.DataFrame, home_col: str, away_col: str, xi: float = 0.005):
    """Same MLE structure as DixonColesModel.fit but for an arbitrary count
    response (here: shots on target instead of goals), no rho correction —
    rho was validated for goals specifically, not assumed to transfer."""
    teams = sorted(pd.unique(history[["HomeTeam", "AwayTeam"]].values.ravel()))
    n = len(teams)
    idx = {t: i for i, t in enumerate(teams)}

    max_date = history["kickoff_utc"].max()
    days_ago = (max_date - history["kickoff_utc"]).dt.total_seconds() / 86400.0
    weights = np.exp(-xi * days_ago.values)

    home_idx = history["HomeTeam"].map(idx).values
    away_idx = history["AwayTeam"].map(idx).values
    h = history[home_col].values
    a = history[away_col].values

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
    return attack, defense, home_adv


def independent_poisson_matrix(home_xg: float, away_xg: float) -> np.ndarray:
    home_probs = poisson.pmf(np.arange(MAX_GOALS + 1), home_xg)
    away_probs = poisson.pmf(np.arange(MAX_GOALS + 1), away_xg)
    matrix = np.outer(home_probs, away_probs)
    return matrix / matrix.sum()


def outcome_probs(matrix: np.ndarray) -> tuple[float, float, float]:
    home_win = float(np.tril(matrix, -1).sum())
    draw = float(np.trace(matrix))
    away_win = float(np.triu(matrix, 1).sum())
    return home_win, draw, away_win


def walk_forward(df: pd.DataFrame, eval_df: pd.DataFrame) -> pd.DataFrame:
    eval_df = eval_df.copy()
    eval_df["week"] = eval_df["kickoff_utc"].dt.to_period("W")
    rows = []
    for week, week_matches in eval_df.groupby("week"):
        week_start = week_matches["kickoff_utc"].min()
        history = df[df["kickoff_utc"] < week_start]
        history_shots = history.dropna(subset=["HST", "AST"])
        if history.empty or len(history_shots) < 50:
            continue

        goals_model = DixonColesModel.fit(history, xi=0.005)
        shot_attack, shot_defense, shot_home_adv = fit_poisson_rates(history_shots, "HST", "AST")
        conversion_rate = history["FTHG"].sum() / history_shots["HST"].sum() if history_shots["HST"].sum() > 0 else None
        away_conversion_rate = history["FTAG"].sum() / history_shots["AST"].sum() if history_shots["AST"].sum() > 0 else None

        for _, row in week_matches.iterrows():
            home, away = row["HomeTeam"], row["AwayTeam"]
            if home not in shot_attack or away not in shot_attack or conversion_rate is None:
                continue

            goals_pred = goals_model.predict(home, away)

            home_xsot = float(np.exp(shot_attack[home] + shot_defense[away] + shot_home_adv))
            away_xsot = float(np.exp(shot_attack[away] + shot_defense[home]))
            shots_home_xg = home_xsot * conversion_rate
            shots_away_xg = away_xsot * away_conversion_rate
            shots_matrix = independent_poisson_matrix(shots_home_xg, shots_away_xg)
            shots_home, shots_draw, shots_away = outcome_probs(shots_matrix)

            actual = "H" if row["FTHG"] > row["FTAG"] else ("A" if row["FTAG"] > row["FTHG"] else "D")
            rows.append({
                "goals_home": goals_pred["home_win_prob"], "goals_draw": goals_pred["draw_prob"], "goals_away": goals_pred["away_win_prob"],
                "shots_home": shots_home, "shots_draw": shots_draw, "shots_away": shots_away,
                "actual": actual,
            })
    return pd.DataFrame(rows)


def blend(goals_probs: np.ndarray, shots_probs: np.ndarray, w_shots: float) -> np.ndarray:
    p = w_shots * shots_probs + (1 - w_shots) * goals_probs
    return p / p.sum(axis=1, keepdims=True)


def main() -> None:
    df = pd.read_parquet(PROCESSED_PATH).sort_values("kickoff_utc").reset_index(drop=True)

    warmup_cutoff = df[df["season"] == "2021-2022"]["kickoff_utc"].max()
    val_df = df[(df["kickoff_utc"] > warmup_cutoff) & (df["season"] == "2022-2023")]
    test_df = df[df["season"].isin(["2023-2024", "2024-2025"])]

    print("Computing validation-season (2022-2023) walk-forward goals-model + shots-model probabilities...")
    val_res = walk_forward(df, val_df)
    print("Computing TEST-season (2023-2025) walk-forward goals-model + shots-model probabilities...")
    test_res = walk_forward(df, test_df)

    y_val = val_res["actual"].map({"H": 0, "D": 1, "A": 2}).values
    y_test = test_res["actual"].map({"H": 0, "D": 1, "A": 2}).values
    val_goals = val_res[["goals_home", "goals_draw", "goals_away"]].values
    val_shots = val_res[["shots_home", "shots_draw", "shots_away"]].values
    test_goals = test_res[["goals_home", "goals_draw", "goals_away"]].values
    test_shots = test_res[["shots_home", "shots_draw", "shots_away"]].values

    def val_nll(w):
        return log_loss(y_val, blend(val_goals, val_shots, w), labels=[0, 1, 2])

    result = minimize_scalar(val_nll, bounds=(0.0, 1.0), method="bounded")
    best_w = result.x
    print(f"\nBest shots-model weight (validation only): w_shots={best_w:.3f}")
    print(f"  Validation Log Loss — goals alone: {log_loss(y_val, val_goals, labels=[0,1,2]):.4f}, "
          f"shots alone: {log_loss(y_val, val_shots, labels=[0,1,2]):.4f}, blend: {result.fun:.4f}")

    def report(name, probs, y):
        ll = log_loss(y, probs, labels=[0, 1, 2])
        one_hot = np.zeros_like(probs)
        one_hot[np.arange(len(y)), y] = 1
        brier = float(np.mean(np.sum((probs - one_hot) ** 2, axis=1)))
        acc = float((probs.argmax(axis=1) == y).mean())
        print(f"{name:<28} LogLoss={ll:.4f}  Brier={brier:.4f}  Accuracy={acc:.4f}")

    test_blend = blend(test_goals, test_shots, best_w)
    print(f"\nTEST set ({len(y_test)} matches, 2023-2025), weight chosen on validation only:")
    report("Dixon-Coles (goals) alone", test_goals, y_test)
    report("Shots-on-target model alone", test_shots, y_test)
    report(f"Blend (w_shots={best_w:.2f})", test_blend, y_test)
    print("\nMarket (Pinnacle) reference on the same test window: LogLoss=0.9330  Brier=0.5505  Accuracy=0.5750")


if __name__ == "__main__":
    main()
