"""
Find the blend weight between our Dixon-Coles model and real market odds
that minimizes Log Loss — replacing the arbitrary 70% market / 30% model
split used in prediction_service.predict_upcoming() with a value actually
validated on real, held-out data.

Same train/validation/test discipline as the rest of the project:
- Validation: 2022-2023 walk-forward predictions -> pick the best weight here.
- Test: 2023-2024 + 2024-2025 (same window as compare_vs_market.py) -> apply
  the validation-chosen weight unchanged, report the result honestly.

Real market probabilities come from Pinnacle closing odds (PSCH/PSCD/PSCA)
in our own downloaded CSVs, de-vigged the same way as compare_vs_market.py.
The Odds API (live) has no historical archive, so this is the only real
market signal we can backtest against — but it's the same de-vigged
average-market signal in spirit as what market_odds.py fetches live.
"""
from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
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
    inv_h, inv_d, inv_a = 1 / row["PSCH"], 1 / row["PSCD"], 1 / row["PSCA"]
    total = inv_h + inv_d + inv_a
    return inv_h / total, inv_d / total, inv_a / total


def walk_forward_model_vs_market(df: pd.DataFrame, eval_df: pd.DataFrame, market: pd.DataFrame) -> pd.DataFrame:
    eval_df = eval_df.copy()
    eval_df["week"] = eval_df["kickoff_utc"].dt.to_period("W")
    rows = []
    for week, week_matches in eval_df.groupby("week"):
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
            mh, md, ma = market_implied_probs(merged.iloc[0])
            pred = model.predict(row["HomeTeam"], row["AwayTeam"])
            actual = "H" if row["FTHG"] > row["FTAG"] else ("A" if row["FTAG"] > row["FTHG"] else "D")
            rows.append({
                "model_home": pred["home_win_prob"], "model_draw": pred["draw_prob"], "model_away": pred["away_win_prob"],
                "market_home": mh, "market_draw": md, "market_away": ma,
                "actual": actual,
            })
    return pd.DataFrame(rows)


def blend(model_probs: np.ndarray, market_probs: np.ndarray, w_market: float) -> np.ndarray:
    p = w_market * market_probs + (1 - w_market) * model_probs
    return p / p.sum(axis=1, keepdims=True)


def main() -> None:
    market = load_market_odds()
    df = pd.read_parquet(PROCESSED_PATH).sort_values("kickoff_utc").reset_index(drop=True)
    df["kickoff_date"] = pd.to_datetime(df["kickoff_utc"]).dt.normalize()
    market["kickoff_date"] = pd.to_datetime(market["kickoff_date"]).dt.normalize()

    warmup_cutoff = df[df["season"] == "2021-2022"]["kickoff_utc"].max()
    val_df = df[(df["kickoff_utc"] > warmup_cutoff) & (df["season"] == "2022-2023")]
    test_df = df[df["season"].isin(["2023-2024", "2024-2025"])]

    print("Computing validation-season (2022-2023) walk-forward model + market probabilities...")
    val_res = walk_forward_model_vs_market(df, val_df, market)
    print("Computing TEST-season (2023-2025) walk-forward model + market probabilities...")
    test_res = walk_forward_model_vs_market(df, test_df, market)

    y_val = val_res["actual"].map({"H": 0, "D": 1, "A": 2}).values
    y_test = test_res["actual"].map({"H": 0, "D": 1, "A": 2}).values
    val_model = val_res[["model_home", "model_draw", "model_away"]].values
    val_market = val_res[["market_home", "market_draw", "market_away"]].values
    test_model = test_res[["model_home", "model_draw", "model_away"]].values
    test_market = test_res[["market_home", "market_draw", "market_away"]].values

    def val_nll(w: float) -> float:
        return log_loss(y_val, blend(val_model, val_market, w), labels=[0, 1, 2])

    result = minimize_scalar(val_nll, bounds=(0.0, 1.0), method="bounded")
    best_w = result.x
    print(f"\nBest market weight (validation only): w_market={best_w:.3f}, w_model={1 - best_w:.3f}")
    print(f"  Validation Log Loss — model alone: {log_loss(y_val, val_model, labels=[0,1,2]):.4f}, "
          f"market alone: {log_loss(y_val, val_market, labels=[0,1,2]):.4f}, "
          f"blend: {result.fun:.4f}")

    def report(name, probs, y):
        ll = log_loss(y, probs, labels=[0, 1, 2])
        one_hot = np.zeros_like(probs)
        one_hot[np.arange(len(y)), y] = 1
        brier = float(np.mean(np.sum((probs - one_hot) ** 2, axis=1)))
        acc = float((probs.argmax(axis=1) == y).mean())
        print(f"{name:<28} LogLoss={ll:.4f}  Brier={brier:.4f}  Accuracy={acc:.4f}")

    test_blend = blend(test_model, test_market, best_w)
    print(f"\nTEST set ({len(y_test)} matches, 2023-2025), weight chosen on validation only:")
    report("Dixon-Coles alone", test_model, y_test)
    report("Market (Pinnacle) alone", test_market, y_test)
    report(f"Blend (w_market={best_w:.2f})", test_blend, y_test)

    # Also report the fixed 70% we shipped, purely for comparison.
    test_blend_70 = blend(test_model, test_market, 0.70)
    report("Blend (w_market=0.70, old)", test_blend_70, y_test)


if __name__ == "__main__":
    main()
