"""Re-scores the Poisson baseline restricted to the same TEST window used for
Dixon-Coles (2023-2024 + 2024-2025) so the two models are compared apples to
apples, instead of comparing against the original run's wider window."""
from __future__ import annotations

import os

from ml.evaluation.backtest_dixon_coles import compute_metrics
from ml.evaluation.backtest_poisson import DATA_PATH
from ml.models.poisson_baseline import PoissonModel

import pandas as pd


def main() -> None:
    df = pd.read_parquet(DATA_PATH).sort_values("kickoff_utc").reset_index(drop=True)
    test_df = df[df["season"].isin(["2023-2024", "2024-2025"])].copy()
    test_df["week"] = test_df["kickoff_utc"].dt.to_period("W")

    results = []
    for week, week_matches in test_df.groupby("week"):
        week_start = week_matches["kickoff_utc"].min()
        history = df[df["kickoff_utc"] < week_start]
        model = PoissonModel.fit(history)
        for _, row in week_matches.iterrows():
            pred = model.predict(row["HomeTeam"], row["AwayTeam"])
            actual = "H" if row["FTHG"] > row["FTAG"] else ("A" if row["FTAG"] > row["FTHG"] else "D")
            results.append({
                "home_win_prob": pred["home_win_prob"],
                "draw_prob": pred["draw_prob"],
                "away_win_prob": pred["away_win_prob"],
                "actual_result": actual,
            })

    metrics = compute_metrics(pd.DataFrame(results))
    print(f"Poisson baseline — SAME TEST set (2023-2024 + 2024-2025), {metrics['n_predictions']} matches:")
    print(f"  Log Loss     : {metrics['log_loss']:.4f}")
    print(f"  Brier Score  : {metrics['brier_score']:.4f}")
    print(f"  Accuracy     : {metrics['accuracy']:.4f}")


if __name__ == "__main__":
    main()
