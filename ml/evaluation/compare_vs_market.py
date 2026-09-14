"""
Honest comparison: our model's walk-forward predictions vs real closing
bookmaker odds (Pinnacle, PSCH/PSCD/PSCA columns), on the exact same
matches. Pinnacle is used because it is widely considered the sharpest
("most efficient") bookmaker in the market, making it the fairest baseline
for "does this model beat the market" rather than a softer bookmaker.

This does NOT prove our model beats the market in general — it is a
backtest over ~4 seasons of Premier League matches, not a live betting
track record, and closing odds already reflect all public information
(team news, weather, etc.) that our model does not use. Any edge shown
here should be read as "how does the model's calibration compare to the
market's", not as a guarantee of profitable betting.
"""
from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss

from ml.models.dixon_coles import DixonColesModel

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw")
PROCESSED_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed", "matches.parquet")


def load_market_odds() -> pd.DataFrame:
    frames = []
    for path in sorted(glob.glob(os.path.join(RAW_DIR, "E0_*.csv"))):
        df = pd.read_csv(path)
        cols = ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"]
        odds_cols = [c for c in ["PSCH", "PSCD", "PSCA"] if c in df.columns]
        if len(odds_cols) < 3:
            continue
        sub = df[cols + odds_cols].dropna(subset=odds_cols)
        sub["kickoff_date"] = pd.to_datetime(sub["Date"], format="%d/%m/%Y")
        frames.append(sub)
    return pd.concat(frames, ignore_index=True)


def market_implied_probs(row) -> tuple[float, float, float]:
    """Converts closing odds to probabilities with the overround removed
    (proportional de-vig) — standard practice, not our invention."""
    inv_h, inv_d, inv_a = 1 / row["PSCH"], 1 / row["PSCD"], 1 / row["PSCA"]
    total = inv_h + inv_d + inv_a
    return inv_h / total, inv_d / total, inv_a / total


def main() -> None:
    market = load_market_odds()
    df = pd.read_parquet(PROCESSED_PATH).sort_values("kickoff_utc").reset_index(drop=True)
    df["kickoff_date"] = pd.to_datetime(df["kickoff_utc"]).dt.normalize()

    # Test window: same as the Dixon-Coles walk-forward backtest (2023-2024 + 2024-2025),
    # so this is comparable to the numbers already reported in /model/performance.
    test_df = df[df["season"].isin(["2023-2024", "2024-2025"])].copy()
    test_df["week"] = test_df["kickoff_utc"].dt.to_period("W")

    results = []
    for week, week_matches in test_df.groupby("week"):
        week_start = week_matches["kickoff_utc"].min()
        history = df[df["kickoff_utc"] < week_start]
        if history.empty:
            continue
        model = DixonColesModel.fit(history, xi=0.005)

        for _, row in week_matches.iterrows():
            merged = market[
                (market["HomeTeam"] == row["HomeTeam"])
                & (market["AwayTeam"] == row["AwayTeam"])
                & (market["kickoff_date"] == row["kickoff_date"])
            ]
            if merged.empty:
                continue
            m = merged.iloc[0]
            mh, md, ma = market_implied_probs(m)

            pred = model.predict(row["HomeTeam"], row["AwayTeam"])
            actual = "H" if row["FTHG"] > row["FTAG"] else ("A" if row["FTAG"] > row["FTHG"] else "D")

            results.append({
                "model_home": pred["home_win_prob"], "model_draw": pred["draw_prob"], "model_away": pred["away_win_prob"],
                "market_home": mh, "market_draw": md, "market_away": ma,
                "actual": actual,
            })

    res = pd.DataFrame(results)
    y_true = res["actual"].map({"H": 0, "D": 1, "A": 2}).values
    model_probs = res[["model_home", "model_draw", "model_away"]].values
    market_probs = res[["market_home", "market_draw", "market_away"]].values

    model_ll = log_loss(y_true, model_probs, labels=[0, 1, 2])
    market_ll = log_loss(y_true, market_probs, labels=[0, 1, 2])

    one_hot = np.zeros_like(model_probs)
    one_hot[np.arange(len(y_true)), y_true] = 1
    model_brier = float(np.mean(np.sum((model_probs - one_hot) ** 2, axis=1)))
    market_brier = float(np.mean(np.sum((market_probs - one_hot) ** 2, axis=1)))

    model_acc = float((model_probs.argmax(axis=1) == y_true).mean())
    market_acc = float((market_probs.argmax(axis=1) == y_true).mean())

    print(f"Comparison on {len(res)} real matches with Pinnacle closing odds available (2023-2025):\n")
    print(f"{'Metric':<12} {'Dixon-Coles':>12} {'Marché (Pinnacle)':>20}")
    print(f"{'Log Loss':<12} {model_ll:>12.4f} {market_ll:>20.4f}  ({'modèle gagne' if model_ll < market_ll else 'marché gagne'})")
    print(f"{'Brier':<12} {model_brier:>12.4f} {market_brier:>20.4f}  ({'modèle gagne' if model_brier < market_brier else 'marché gagne'})")
    print(f"{'Accuracy':<12} {model_acc:>12.4f} {market_acc:>20.4f}  ({'modèle gagne' if model_acc > market_acc else 'marché gagne'})")


if __name__ == "__main__":
    main()
