"""
Walk-forward backtest of Dixon-Coles, following the same protocol as
ml/evaluation/backtest_poisson.py so the two are directly comparable.

Protocol:
- 2021-2022: warm-up only, never scored.
- 2022-2023: VALIDATION — used only to pick the time-decay xi via grid
  search on log loss. Never touched again after that choice is made.
- 2023-2024 + 2024-2025: TEST — scored once, with xi fixed from validation.

This mirrors the project's train/validation/test discipline: xi is not
picked by taste, and it is never tuned against the test set.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss

from ml.models.dixon_coles import DixonColesModel

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed", "matches.parquet")
XI_GRID = [0.0, 0.0005, 0.001, 0.0018, 0.003, 0.005]


def _weekly_walk_forward(df: pd.DataFrame, eval_df: pd.DataFrame, xi: float) -> pd.DataFrame:
    eval_df = eval_df.copy()
    eval_df["week"] = eval_df["kickoff_utc"].dt.to_period("W")
    results = []

    for week, week_matches in eval_df.groupby("week"):
        week_start = week_matches["kickoff_utc"].min()
        history = df[df["kickoff_utc"] < week_start]
        if history.empty:
            continue
        model = DixonColesModel.fit(history, xi=xi)

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
            })

    return pd.DataFrame(results)


def _log_loss_of(results: pd.DataFrame) -> float:
    y_true = results["actual_result"].map({"H": 0, "D": 1, "A": 2}).values
    probs = results[["home_win_prob", "draw_prob", "away_win_prob"]].values
    probs = probs / probs.sum(axis=1, keepdims=True)
    return log_loss(y_true, probs, labels=[0, 1, 2])


def select_xi(df: pd.DataFrame) -> float:
    warmup_cutoff = df[df["season"] == "2021-2022"]["kickoff_utc"].max()
    val_df = df[(df["kickoff_utc"] > warmup_cutoff) & (df["season"] == "2022-2023")]

    print("Validation grid search for xi (time-decay rate), on 2022-2023 only:")
    best_xi, best_ll = None, np.inf
    for xi in XI_GRID:
        results = _weekly_walk_forward(df, val_df, xi)
        ll = _log_loss_of(results)
        print(f"  xi={xi:<8} log_loss={ll:.4f}")
        if ll < best_ll:
            best_xi, best_ll = xi, ll

    print(f"-> selected xi={best_xi} (best validation log loss {best_ll:.4f})\n")
    return best_xi


def compute_metrics(results: pd.DataFrame) -> dict:
    y_true = results["actual_result"].map({"H": 0, "D": 1, "A": 2}).values
    probs = results[["home_win_prob", "draw_prob", "away_win_prob"]].values
    probs = probs / probs.sum(axis=1, keepdims=True)

    ll = log_loss(y_true, probs, labels=[0, 1, 2])
    one_hot = np.zeros_like(probs)
    one_hot[np.arange(len(y_true)), y_true] = 1
    brier = float(np.mean(np.sum((probs - one_hot) ** 2, axis=1)))
    accuracy = float((probs.argmax(axis=1) == y_true).mean())

    return {"n_predictions": len(results), "log_loss": ll, "brier_score": brier, "accuracy": accuracy}


def main() -> None:
    df = pd.read_parquet(DATA_PATH).sort_values("kickoff_utc").reset_index(drop=True)

    xi = select_xi(df)

    test_df = df[df["season"].isin(["2023-2024", "2024-2025"])]
    test_results = _weekly_walk_forward(df, test_df, xi)
    metrics = compute_metrics(test_results)

    out_path = os.path.join(os.path.dirname(DATA_PATH), "backtest_dixon_coles_results.parquet")
    test_results.to_parquet(out_path, index=False)

    print(f"Dixon-Coles (xi={xi}) — TEST set (2023-2024 + 2024-2025), {metrics['n_predictions']} matches:")
    print(f"  Log Loss     : {metrics['log_loss']:.4f}")
    print(f"  Brier Score  : {metrics['brier_score']:.4f}")
    print(f"  Accuracy     : {metrics['accuracy']:.4f}")
    print(f"Predictions saved to {out_path}")


if __name__ == "__main__":
    main()
