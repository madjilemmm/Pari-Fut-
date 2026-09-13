"""
Serves predictions strictly from real historical data (data/processed/matches.parquet).

IMPORTANT — Phase 1 has no live fixtures/odds/injuries provider wired in.
"Matches" exposed by this API are the real historical Premier League matches
already ingested; predicting one always refits the model using ONLY matches
that occurred strictly before its kickoff, so the numbers are the same ones
the walk-forward backtest already validated — nothing here is invented.
"""
from __future__ import annotations

import os

import pandas as pd

from ml.models.dixon_coles import DixonColesModel
from ml.models.elo import EloModel

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed", "matches.parquet")
MODEL_VERSION = "edge_v0.2_dixon_coles"
SELECTED_XI = 0.005  # chosen via validation grid search, see ml/evaluation/backtest_dixon_coles.py

_df: pd.DataFrame | None = None


def _load_df() -> pd.DataFrame:
    global _df
    if _df is None:
        if not os.path.exists(DATA_PATH):
            raise FileNotFoundError(
                "Données indisponibles: exécutez jobs/ingest_football_data_csv.py d'abord."
            )
        _df = pd.read_parquet(DATA_PATH).sort_values("kickoff_utc").reset_index(drop=True)
        _df["match_id"] = _df.index.astype(str)
    return _df


def list_matches(limit: int = 20) -> list[dict]:
    df = _load_df()
    rows = df.tail(limit)
    return [
        {
            "match_id": row["match_id"],
            "home_team": row["HomeTeam"],
            "away_team": row["AwayTeam"],
            "kickoff_utc": row["kickoff_utc"].isoformat(),
            "league": "Premier League",
        }
        for _, row in rows.iterrows()
    ]


def _confidence_score(history_len_home: int, history_len_away: int) -> tuple[float, str]:
    """Data-quality score, NOT a win probability. Penalizes thin history and
    the total absence of injuries/lineups/odds data in Phase 1."""
    min_history = min(history_len_home, history_len_away)
    data_volume_score = min(100.0, min_history * 2.5)  # saturates around 40 past matches/team

    # No injury/lineup/odds provider wired yet -> flat penalty, explicit and documented.
    missing_sources_penalty = 25.0

    score = max(0.0, data_volume_score - missing_sources_penalty)
    note = (
        "Score basé uniquement sur le volume d'historique disponible. "
        "Compositions, blessures et cotes de marché non disponibles en Phase 1 "
        "(pénalité fixe appliquée plutôt que de les ignorer silencieusement)."
    )
    return round(score, 1), note


def predict_match(match_id: str) -> dict:
    df = _load_df()
    match = df[df["match_id"] == match_id]
    if match.empty:
        raise KeyError(f"match_id {match_id} introuvable")
    row = match.iloc[0]

    history = df[df["kickoff_utc"] < row["kickoff_utc"]]
    if len(history) < 20:
        raise ValueError("Historique insuffisant pour ce match (Donnée indisponible).")

    model = DixonColesModel.fit(history, xi=SELECTED_XI)
    pred = model.predict(row["HomeTeam"], row["AwayTeam"])

    home_hist = len(history[(history["HomeTeam"] == row["HomeTeam"]) | (history["AwayTeam"] == row["HomeTeam"])])
    away_hist = len(history[(history["HomeTeam"] == row["AwayTeam"]) | (history["AwayTeam"] == row["AwayTeam"])])
    confidence, note = _confidence_score(home_hist, away_hist)

    return {
        "match_id": match_id,
        "home_team": row["HomeTeam"],
        "away_team": row["AwayTeam"],
        "model_version": MODEL_VERSION,
        "confidence_score": confidence,
        "confidence_note": note,
        **pred,
    }


def elo_ratings_snapshot(as_of_match_id: str) -> dict:
    df = _load_df()
    match = df[df["match_id"] == as_of_match_id]
    if match.empty:
        raise KeyError(f"match_id {as_of_match_id} introuvable")
    row = match.iloc[0]
    history = df[df["kickoff_utc"] < row["kickoff_utc"]]
    elo = EloModel.fit(history)
    return {
        "home_team": row["HomeTeam"],
        "away_team": row["AwayTeam"],
        "home_elo": round(elo.rating(row["HomeTeam"]), 1),
        "away_elo": round(elo.rating(row["AwayTeam"]), 1),
    }
