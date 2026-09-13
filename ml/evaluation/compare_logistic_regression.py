"""
Quick, honest comparison: does a simple ML model (Logistic Regression on
Elo-rating difference) beat the Poisson baseline out-of-sample?

Kept intentionally minimal for Phase 1 — feature is just the Elo rating gap
computed walk-forward (no leakage: Elo is refit per week using only past
matches, exactly like the Poisson/Dixon-Coles backtests).
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss

from ml.models.elo import EloModel

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed", "matches.parquet")


def build_elo_features(df: pd.DataFrame) -> pd.DataFrame:
    """Walk-forward Elo diff feature: refit Elo weekly using only past matches."""
    df = df.sort_values("kickoff_utc").reset_index(drop=True)
    df["week"] = df["kickoff_utc"].dt.to_period("W")
    rows = []
    for week, week_matches in df.groupby("week"):
        week_start = week_matches["kickoff_utc"].min()
        history = df[df["kickoff_utc"] < week_start]
        if history.empty:
            continue
        elo = EloModel.fit(history)
        for _, row in week_matches.iterrows():
            rows.append({
                "kickoff_utc": row["kickoff_utc"],
                "elo_diff": elo.rating(row["HomeTeam"]) - elo.rating(row["AwayTeam"]) + elo.home_advantage_elo,
                "actual_result": "H" if row["FTHG"] > row["FTAG"] else ("A" if row["FTAG"] > row["FTHG"] else "D"),
            })
    return pd.DataFrame(rows)


def main() -> None:
    df = pd.read_parquet(DATA_PATH)
    warmup_cutoff = df[df["season"] == "2021-2022"]["kickoff_utc"].max()
    eval_df = df[df["kickoff_utc"] > warmup_cutoff]

    features = build_elo_features(pd.concat([df[df["season"] == "2021-2022"], eval_df]))
    features = features[features["kickoff_utc"] > warmup_cutoff].reset_index(drop=True)

    y = features["actual_result"].map({"H": 0, "D": 1, "A": 2}).values
    X = features[["elo_diff"]].values

    # Chronological split: first 70% train the logistic model, last 30% test it —
    # never fit on the same matches used to score it.
    split = int(len(features) * 0.7)
    clf = LogisticRegression(max_iter=1000)
    clf.fit(X[:split], y[:split])
    probs = clf.predict_proba(X[split:])
    ll_lr = log_loss(y[split:], probs, labels=[0, 1, 2])
    acc_lr = float((probs.argmax(axis=1) == y[split:]).mean())

    print(f"Logistic Regression on walk-forward Elo diff, {len(y) - split} held-out matches:")
    print(f"  Log Loss : {ll_lr:.4f}")
    print(f"  Accuracy : {acc_lr:.4f}")
    print()
    print("Poisson baseline reference (full backtest, wider window): LogLoss=1.1215, Accuracy=0.5377")
    print("NOTE: windows differ (Elo comparison uses a 30% chronological tail, not the exact")
    print("same matches) — this is a quick directional check, not a final head-to-head.")
    print("Conclusion: " + (
        "Logistic Regression on Elo alone does NOT clearly beat the baseline enough to justify "
        "replacing it yet — keep Poisson/Dixon-Coles as the production model and treat this as a "
        "candidate ensemble input, not a Phase 1 upgrade."
        if ll_lr >= 1.05 else
        "Logistic Regression shows a promising log loss improvement — worth a proper "
        "same-window backtest before adopting it."
    ))


if __name__ == "__main__":
    main()
