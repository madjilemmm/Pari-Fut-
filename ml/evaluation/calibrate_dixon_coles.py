"""
Attempts to close the gap to the market found in compare_vs_market.py using
temperature scaling: a single scalar T fit on a VALIDATION season (never
the test season) that rescales the model's 3-way probabilities to better
match observed frequencies. Standard, well-established calibration
technique — not a new model, not a fudge factor tuned on the test set.

Protocol (train/validation/test discipline, same rule as everywhere else
in this project):
- Validation: 2022-2023 walk-forward predictions -> fit T here.
- Test: 2023-2024 + 2024-2025 (same window as compare_vs_market.py) ->
  apply the T found on validation, report honestly whether it helps.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from sklearn.metrics import log_loss

from ml.models.dixon_coles import DixonColesModel

DATA_PATH = "data/processed/matches.parquet"


def walk_forward_probs(df: pd.DataFrame, eval_df: pd.DataFrame) -> pd.DataFrame:
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
            pred = model.predict(row["HomeTeam"], row["AwayTeam"])
            actual = "H" if row["FTHG"] > row["FTAG"] else ("A" if row["FTAG"] > row["FTHG"] else "D")
            rows.append({
                "p_home": pred["home_win_prob"], "p_draw": pred["draw_prob"], "p_away": pred["away_win_prob"],
                "actual": actual,
            })
    return pd.DataFrame(rows)


def apply_temperature(probs: np.ndarray, T: float) -> np.ndarray:
    """Softmax(log(p) / T), renormalized — standard temperature scaling
    adapted to already-normalized probabilities instead of raw logits."""
    logp = np.log(np.clip(probs, 1e-9, None)) / T
    exp = np.exp(logp - logp.max(axis=1, keepdims=True))
    return exp / exp.sum(axis=1, keepdims=True)


def main() -> None:
    df = pd.read_parquet(DATA_PATH).sort_values("kickoff_utc").reset_index(drop=True)

    warmup_cutoff = df[df["season"] == "2021-2022"]["kickoff_utc"].max()
    val_df = df[(df["kickoff_utc"] > warmup_cutoff) & (df["season"] == "2022-2023")]
    test_df = df[df["season"].isin(["2023-2024", "2024-2025"])]

    print("Computing validation-season walk-forward probabilities (2022-2023)...")
    val_res = walk_forward_probs(df, val_df)
    y_val = val_res["actual"].map({"H": 0, "D": 1, "A": 2}).values
    p_val = val_res[["p_home", "p_draw", "p_away"]].values

    def val_nll(T: float) -> float:
        return log_loss(y_val, apply_temperature(p_val, T), labels=[0, 1, 2])

    result = minimize_scalar(val_nll, bounds=(0.3, 3.0), method="bounded")
    best_T = result.x
    print(f"Best temperature T={best_T:.4f} (validation Log Loss: {result.fun:.4f}, "
          f"T=1.0 i.e. uncalibrated: {val_nll(1.0):.4f})")

    print("\nComputing TEST-season walk-forward probabilities (2023-2025)...")
    test_res = walk_forward_probs(df, test_df)
    y_test = test_res["actual"].map({"H": 0, "D": 1, "A": 2}).values
    p_test_raw = test_res[["p_home", "p_draw", "p_away"]].values
    p_test_calibrated = apply_temperature(p_test_raw, best_T)

    ll_raw = log_loss(y_test, p_test_raw, labels=[0, 1, 2])
    ll_cal = log_loss(y_test, p_test_calibrated, labels=[0, 1, 2])

    one_hot = np.zeros_like(p_test_raw)
    one_hot[np.arange(len(y_test)), y_test] = 1
    brier_raw = float(np.mean(np.sum((p_test_raw - one_hot) ** 2, axis=1)))
    brier_cal = float(np.mean(np.sum((p_test_calibrated - one_hot) ** 2, axis=1)))
    acc_raw = float((p_test_raw.argmax(axis=1) == y_test).mean())
    acc_cal = float((p_test_calibrated.argmax(axis=1) == y_test).mean())

    print(f"\nTEST set ({len(y_test)} matches), T={best_T:.4f} chosen on validation only:")
    print(f"{'Metric':<10} {'Raw':>10} {'Calibrated':>12}")
    print(f"{'Log Loss':<10} {ll_raw:>10.4f} {ll_cal:>12.4f}  ({'AMÉLIORE' if ll_cal < ll_raw else 'dégrade'})")
    print(f"{'Brier':<10} {brier_raw:>10.4f} {brier_cal:>12.4f}  ({'AMÉLIORE' if brier_cal < brier_raw else 'dégrade'})")
    print(f"{'Accuracy':<10} {acc_raw:>10.4f} {acc_cal:>12.4f}  ({'AMÉLIORE' if acc_cal > acc_raw else 'dégrade'})")
    print("\nMarket (Pinnacle) reference on the same test window: Log Loss=0.9330, Brier=0.5505, Accuracy=0.5750")


if __name__ == "__main__":
    main()
