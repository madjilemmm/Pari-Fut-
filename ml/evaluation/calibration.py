"""
Calibration analysis + isotonic correction for the 1X2 home-win probability,
fit ONLY on the walk-forward backtest predictions (never on raw training
data) to avoid any leakage into the calibration itself.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss, log_loss

RESULTS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed", "backtest_poisson_results.parquet")


def expected_calibration_error(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (y_prob >= lo) & (y_prob < hi)
        if mask.sum() == 0:
            continue
        acc = y_true[mask].mean()
        conf = y_prob[mask].mean()
        ece += (mask.sum() / len(y_prob)) * abs(acc - conf)
    return float(ece)


def main() -> None:
    df = pd.read_parquet(RESULTS_PATH)
    y_true = (df["actual_result"] == "H").astype(int).values
    y_prob = df["home_win_prob"].values

    ece_before = expected_calibration_error(y_true, y_prob)
    ll_before = log_loss(y_true, y_prob)
    brier_before = brier_score_loss(y_true, y_prob)

    # Split chronologically: first 70% to fit isotonic, last 30% to evaluate
    # (never fit and evaluate calibration on the same matches).
    split = int(len(df) * 0.7)
    iso = IsotonicRegression(out_of_bounds="clip")
    iso.fit(y_prob[:split], y_true[:split])

    y_prob_test_raw = y_prob[split:]
    y_true_test = y_true[split:]
    y_prob_test_calibrated = iso.predict(y_prob_test_raw)

    ece_after = expected_calibration_error(y_true_test, y_prob_test_calibrated)
    ll_after = log_loss(y_true_test, np.clip(y_prob_test_calibrated, 1e-6, 1 - 1e-6))
    brier_after = brier_score_loss(y_true_test, y_prob_test_calibrated)
    ll_raw_same_slice = log_loss(y_true_test, y_prob_test_raw)
    brier_raw_same_slice = brier_score_loss(y_true_test, y_prob_test_raw)

    print("=== Calibration — Poisson baseline, home-win probability ===")
    print(f"Full backtest (uncalibrated): ECE={ece_before:.4f}  LogLoss={ll_before:.4f}  Brier={brier_before:.4f}")
    print()
    print(f"Held-out slice ({len(y_true_test)} matches), RAW vs ISOTONIC-CALIBRATED:")
    print(f"  Raw       : LogLoss={ll_raw_same_slice:.4f}  Brier={brier_raw_same_slice:.4f}")
    print(f"  Calibrated: LogLoss={ll_after:.4f}  Brier={brier_after:.4f}  ECE={ece_after:.4f}")

    frac_pos, mean_pred = calibration_curve(y_true_test, y_prob_test_raw, n_bins=8)
    print("\nReliability diagram (raw), predicted vs observed frequency:")
    for p, o in zip(mean_pred, frac_pos):
        print(f"  predicted~{p:.2f} -> observed {o:.2f}")

    out_path = os.path.join(os.path.dirname(RESULTS_PATH), "isotonic_calibrator.pkl")
    import pickle
    with open(out_path, "wb") as f:
        pickle.dump(iso, f)
    print(f"\nCalibrator saved to {out_path}")


if __name__ == "__main__":
    main()
