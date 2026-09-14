"""
Backfills a finished Premier League season from football-data.org into
data/processed/matches.parquet, appended alongside the football-data.co.uk
CSV history (jobs/ingest_football_data_csv.py).

Why this exists: our original CSV history (data/raw/*.csv) stops at the end
of the 2024-2025 season. The 2025-2026 season is not in it, leaving a real
gap between the last training data and the current 2026-2027 season, which
degrades predictions for the current season (team strength estimates go
stale, and clubs promoted in 2025-2026 have zero history). This closes that
gap with REAL match results, not synthetic data.

Requires FOOTBALL_DATA_API_TOKEN. Safe to re-run: matches are de-duplicated
by (HomeTeam, AwayTeam, kickoff date) before being written back out.
"""
from __future__ import annotations

import os
import sys

import httpx
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.services.live_fixtures import _normalize_team_name  # noqa: E402

PROCESSED_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "matches.parquet")
FOOTBALL_DATA_BASE = "https://api.football-data.org/v4"


def fetch_finished_season(season_start_year: int) -> pd.DataFrame:
    token = os.environ.get("FOOTBALL_DATA_API_TOKEN")
    if not token:
        raise RuntimeError("FOOTBALL_DATA_API_TOKEN non configuré — impossible de récupérer la saison.")

    resp = httpx.get(
        f"{FOOTBALL_DATA_BASE}/competitions/PL/matches",
        params={"season": season_start_year, "status": "FINISHED"},
        headers={"X-Auth-Token": token},
        timeout=30.0,
    )
    resp.raise_for_status()
    data = resp.json()

    rows = []
    for m in data.get("matches", []):
        home_goals = m["score"]["fullTime"]["home"]
        away_goals = m["score"]["fullTime"]["away"]
        if home_goals is None or away_goals is None:
            continue
        rows.append({
            "HomeTeam": _normalize_team_name(m["homeTeam"]["shortName"] or m["homeTeam"]["name"]),
            "AwayTeam": _normalize_team_name(m["awayTeam"]["shortName"] or m["awayTeam"]["name"]),
            "FTHG": int(home_goals),
            "FTAG": int(away_goals),
            "kickoff_utc": pd.to_datetime(m["utcDate"]),
            "season": f"{season_start_year}-{season_start_year + 1}",
            "source": "football-data.org",
        })
    return pd.DataFrame(rows)


def main() -> None:
    existing = pd.read_parquet(PROCESSED_PATH)
    season_start = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
    new_season = fetch_finished_season(season_start)

    new_season["kickoff_utc"] = pd.to_datetime(new_season["kickoff_utc"]).dt.tz_localize(None)
    combined = pd.concat([existing, new_season], ignore_index=True)
    combined["kickoff_utc"] = pd.to_datetime(combined["kickoff_utc"])
    before = len(combined)
    combined = combined.drop_duplicates(subset=["HomeTeam", "AwayTeam", "kickoff_utc"], keep="first")
    combined = combined.sort_values("kickoff_utc").reset_index(drop=True)

    combined.to_parquet(PROCESSED_PATH, index=False)
    print(f"Backfilled {len(new_season)} real matches from season {season_start}-{season_start + 1} "
          f"(football-data.org). Total dataset: {len(combined)} matches "
          f"({before - len(combined)} duplicates skipped).")
    print(f"Date range: {combined['kickoff_utc'].min()} -> {combined['kickoff_utc'].max()}")
    print(f"Seasons: {sorted(combined['season'].unique())}")


if __name__ == "__main__":
    main()
