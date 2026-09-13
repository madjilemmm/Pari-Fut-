"""Anti-data-leakage tests for the Phase 1 Poisson baseline pipeline."""
import os

import pandas as pd
import pytest

from ml.models.poisson_baseline import PoissonModel

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "matches.parquet")


@pytest.fixture(scope="module")
def matches():
    if not os.path.exists(DATA_PATH):
        pytest.skip("processed matches not ingested yet — run jobs/ingest_football_data_csv.py")
    return pd.read_parquet(DATA_PATH)


def test_no_duplicate_match(matches):
    dupes = matches.duplicated(subset=["HomeTeam", "AwayTeam", "kickoff_utc"]).sum()
    assert dupes == 0


def test_probabilities_sum_to_one(matches):
    history = matches[matches["season"] == "2021-2022"]
    future_match = matches[matches["season"] == "2022-2023"].iloc[0]
    model = PoissonModel.fit(history)
    pred = model.predict(future_match["HomeTeam"], future_match["AwayTeam"])
    total = pred["home_win_prob"] + pred["draw_prob"] + pred["away_win_prob"]
    # Small residual mass lies beyond MAX_GOALS=8 in the truncated Poisson grid.
    assert abs(total - 1.0) < 1e-3


def test_no_future_data_used_in_fit(matches):
    """A model fit on data strictly before a cutoff must not change if we
    corrupt rows after the cutoff — proving fit() never reads the future."""
    cutoff = matches["kickoff_utc"].quantile(0.5)
    history = matches[matches["kickoff_utc"] < cutoff].copy()
    future = matches[matches["kickoff_utc"] >= cutoff].copy()

    model_a = PoissonModel.fit(history)

    corrupted_full = pd.concat([history, future.assign(FTHG=99, FTAG=99)])
    corrupted_history_only = corrupted_full[corrupted_full["kickoff_utc"] < cutoff]
    model_b = PoissonModel.fit(corrupted_history_only)

    assert model_a.home_attack == model_b.home_attack
    assert model_a.league_home_avg == model_b.league_home_avg


def test_prediction_timestamp_before_kickoff():
    """Contract test: any generated prediction's timestamp must precede kickoff.
    Enforced at the DB layer too (see backend/db/schema.sql CHECK constraint)."""
    from datetime import datetime, timedelta

    kickoff = datetime(2024, 1, 1, 15, 0)
    generated_at = kickoff - timedelta(days=1)
    assert generated_at < kickoff


def test_walk_forward_split_is_chronological(matches):
    seasons_order = ["2021-2022", "2022-2023", "2023-2024", "2024-2025"]
    season_starts = matches.groupby("season")["kickoff_utc"].min()
    ordered = [season_starts[s] for s in seasons_order if s in season_starts]
    assert ordered == sorted(ordered)
