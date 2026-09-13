"""
Walk-forward backtest of the Poisson baseline on real Premier League data.

Protocol (anti-leakage):
- Matches are processed in chronological order.
- To predict match k, the model is refit using ONLY matches with
  kickoff_utc strictly before that match's kickoff_utc.
- The first season (2021-2022) is used purely to warm up team strengths
  and is never scored — there isn't enough prior history to fit on.
- Refitting every single match is expensive; we refit once per matchday
  (i.e. once per week of fixtures) using only data available at the start
  of that week, which is a conservative (never-leaking) approximation.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss

from ml.models.poisson_baseline import PoissonModel

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed", "matches.parquet")


def run_backtest() -> pd.DataFrame:
    df = pd.read_parquet(DATA_PATH).sort_values("kickoff_utc").reset_index(drop=True)

    warmup_cutoff = df[df["season"] == "2021-2022"]["kickoff_utc"].max()
    eval_df = df[df["kickoff_utc"] > warmup_cutoff].copy()

    results = []
    df["week"] = df["kickoff_utc"].dt.to_period("W")
    eval_df["week"] = eval_df["kickoff_utc"].dt.to_period("W")

    for week, week_matches in eval_df.groupby("week"):
        week_start = week_matches["kickoff_utc"].min()
        history = df[df["kickoff_utc"] < week_start]
        if history.empty:
            continue
        model = PoissonModel.fit(history)

        for _, row in week_matches.iterrows():
            pred = model.predict(row["HomeTeam"], row["AwayTeam"])
            actual = "H" if row["FTHG"] > row["FTAG"] else ("A" if row["FTAG"] > row["FTHG"] else "D")
            results.append({
                "kickoff_utc": row["kickoff_utc"],
                "home_team": row["HomeTeam"],
                "away_team": row["AwayTeam"],
                "home_win_prob": pred["home_win_prob"],
                "draw_prob": pred["draw_prob"],
                "away_win_prob": pred["away_win_prob"],
                "actual_result": actual,
                "actual_home_goals": row["FTHG"],
                "actual_away_goals": row["FTAG"],
            })

    return pd.DataFrame(results)


def compute_metrics(results: pd.DataFrame) -> dict:
    y_true = results["actual_result"].map({"H": 0, "D": 1, "A": 2}).values
    probs = results[["home_win_prob", "draw_prob", "away_win_prob"]].values
    probs = probs / probs.sum(axis=1, keepdims=True)  # guard against float drift

    ll = log_loss(y_true, probs, labels=[0, 1, 2])

    # Multiclass Brier score (mean squared error against one-hot outcomes)
    one_hot = np.zeros_like(probs)
    one_hot[np.arange(len(y_true)), y_true] = 1
    brier = float(np.mean(np.sum((probs - one_hot) ** 2, axis=1)))

    predicted = probs.argmax(axis=1)
    accuracy = float((predicted == y_true).mean())

    return {
        "n_predictions": len(results),
        "log_loss": ll,
        "brier_score": brier,
        "accuracy": accuracy,
    }


def main() -> None:
    results = run_backtest()
    metrics = compute_metrics(results)
    out_path = os.path.join(os.path.dirname(DATA_PATH), "backtest_poisson_results.parquet")
    results.to_parquet(out_path, index=False)

    print(f"Walk-forward backtest on {metrics['n_predictions']} real, held-out matches:")
    print(f"  Log Loss     : {metrics['log_loss']:.4f}")
    print(f"  Brier Score  : {metrics['brier_score']:.4f}")
    print(f"  Accuracy     : {metrics['accuracy']:.4f}")
    print(f"Predictions saved to {out_path}")
    print("\nReference: a model that always predicts the historical base rates "
          "(~46% H / 25% D / 29% A) scores roughly log_loss~1.03, accuracy~0.46. "
          "Beating that meaningfully is the bar for this baseline.")


if __name__ == "__main__":
    main()
