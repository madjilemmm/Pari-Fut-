"""
Ensemble: Dixon-Coles + Logistic Regression on walk-forward Elo difference,
with the blend weight optimized on a VALIDATION season only (2022-2023),
then evaluated once on the TEST season (2023-2025) — same window as
compare_vs_market.py, so this is directly comparable to the market numbers
already reported. No number here is chosen by looking at the test set.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss

from ml.models.dixon_coles import DixonColesModel
from ml.models.elo import EloModel

DATA_PATH = "data/processed/matches.parquet"


def walk_forward_dc_and_elo(df: pd.DataFrame, eval_df: pd.DataFrame) -> pd.DataFrame:
    eval_df = eval_df.copy()
    eval_df["week"] = eval_df["kickoff_utc"].dt.to_period("W")
    rows = []
    for week, week_matches in eval_df.groupby("week"):
        week_start = week_matches["kickoff_utc"].min()
        history = df[df["kickoff_utc"] < week_start]
        if history.empty:
            continue
        dc = DixonColesModel.fit(history, xi=0.005)
        elo = EloModel.fit(history)
        for _, row in week_matches.iterrows():
            pred = dc.predict(row["HomeTeam"], row["AwayTeam"])
            elo_diff = elo.rating(row["HomeTeam"]) - elo.rating(row["AwayTeam"]) + elo.home_advantage_elo
            actual = "H" if row["FTHG"] > row["FTAG"] else ("A" if row["FTAG"] > row["FTHG"] else "D")
            rows.append({
                "dc_home": pred["home_win_prob"], "dc_draw": pred["draw_prob"], "dc_away": pred["away_win_prob"],
                "elo_diff": elo_diff, "actual": actual,
            })
    return pd.DataFrame(rows)


def main() -> None:
    df = pd.read_parquet(DATA_PATH).sort_values("kickoff_utc").reset_index(drop=True)
    warmup_cutoff = df[df["season"] == "2021-2022"]["kickoff_utc"].max()
    val_df = df[(df["kickoff_utc"] > warmup_cutoff) & (df["season"] == "2022-2023")]
    test_df = df[df["season"].isin(["2023-2024", "2024-2025"])]

    print("Computing validation-season (2022-2023) walk-forward DC + Elo features...")
    val_res = walk_forward_dc_and_elo(df, val_df)
    print("Computing TEST-season (2023-2025) walk-forward DC + Elo features...")
    test_res = walk_forward_dc_and_elo(df, test_df)

    y_val = val_res["actual"].map({"H": 0, "D": 1, "A": 2}).values
    y_test = test_res["actual"].map({"H": 0, "D": 1, "A": 2}).values

    # Logistic regression on Elo diff, fit on validation only, applied to test —
    # a proper out-of-sample use, not fit directly on the matches it's scored on.
    lr = LogisticRegression(max_iter=1000)
    lr.fit(val_res[["elo_diff"]].values, y_val)
    val_lr_probs = lr.predict_proba(val_res[["elo_diff"]].values)
    test_lr_probs = lr.predict_proba(test_res[["elo_diff"]].values)
    # LogisticRegression orders classes by sorted label; our labels are 0=H,1=D,2=A already sorted.

    val_dc_probs = val_res[["dc_home", "dc_draw", "dc_away"]].values
    test_dc_probs = test_res[["dc_home", "dc_draw", "dc_away"]].values

    def blend(dc_probs, lr_probs, w):
        p = w * dc_probs + (1 - w) * lr_probs
        return p / p.sum(axis=1, keepdims=True)

    def val_nll(w: float) -> float:
        return log_loss(y_val, blend(val_dc_probs, val_lr_probs, w), labels=[0, 1, 2])

    result = minimize_scalar(val_nll, bounds=(0.0, 1.0), method="bounded")
    best_w = result.x
    print(f"\nBest ensemble weight (validation only): w_DixonColes={best_w:.3f}, w_LogReg={1 - best_w:.3f}")
    print(f"  Validation Log Loss — DC alone: {log_loss(y_val, val_dc_probs, labels=[0,1,2]):.4f}, "
          f"LR alone: {log_loss(y_val, val_lr_probs, labels=[0,1,2]):.4f}, "
          f"Ensemble: {result.fun:.4f}")

    test_ensemble_probs = blend(test_dc_probs, test_lr_probs, best_w)

    def report(name, probs):
        ll = log_loss(y_test, probs, labels=[0, 1, 2])
        one_hot = np.zeros_like(probs)
        one_hot[np.arange(len(y_test)), y_test] = 1
        brier = float(np.mean(np.sum((probs - one_hot) ** 2, axis=1)))
        acc = float((probs.argmax(axis=1) == y_test).mean())
        print(f"{name:<22} LogLoss={ll:.4f}  Brier={brier:.4f}  Accuracy={acc:.4f}")

    print(f"\nTEST set ({len(y_test)} matches, 2023-2025), weight chosen on validation only:")
    report("Dixon-Coles alone", test_dc_probs)
    report("LogReg(Elo) alone", test_lr_probs)
    report(f"Ensemble (w={best_w:.2f})", test_ensemble_probs)
    print("\nMarket (Pinnacle) reference on the same test window: LogLoss=0.9330  Brier=0.5505  Accuracy=0.5750")


if __name__ == "__main__":
    main()
