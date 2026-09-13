"""
Ingest historical Premier League results from football-data.co.uk CSV exports
into data/processed/matches.parquet.

Source: https://www.football-data.co.uk/mmz4281/<season>/E0.csv (REAL historical
results, downloaded manually into data/raw/). No invented or simulated data.

Columns used: Date, HomeTeam, AwayTeam, FTHG, FTAG, FTR, HS, AS, HST, AST,
HC, AC. Betting odds columns exist in the source file but are intentionally
NOT ingested yet (Phase 1 has no wired odds provider) — plugging them in
later only requires reading the *closing* columns with their own timestamp.
"""
from __future__ import annotations

import glob
import os

import pandas as pd

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "matches.parquet")

SEASON_BY_FILE = {
    "E0_2122.csv": "2021-2022",
    "E0_2223.csv": "2022-2023",
    "E0_2324.csv": "2023-2024",
    "E0_2425.csv": "2024-2025",
}

KEEP_COLS = [
    "Date", "Time", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR",
    "HTHG", "HTAG", "HS", "AS", "HST", "AST", "HC", "AC",
]


def load_all() -> pd.DataFrame:
    frames = []
    for path in sorted(glob.glob(os.path.join(RAW_DIR, "E0_*.csv"))):
        fname = os.path.basename(path)
        season = SEASON_BY_FILE.get(fname)
        if season is None:
            continue
        df = pd.read_csv(path)
        df = df[[c for c in KEEP_COLS if c in df.columns]].copy()
        df["season"] = season
        df["source"] = "football-data.co.uk"
        frames.append(df)
    full = pd.concat(frames, ignore_index=True)

    time_col = full["Time"].fillna("15:00") if "Time" in full.columns else "15:00"
    full["kickoff_utc"] = pd.to_datetime(
        full["Date"] + " " + time_col, format="%d/%m/%Y %H:%M", errors="coerce"
    )
    # A handful of very old rows have no Time column; fall back to date-only.
    mask = full["kickoff_utc"].isna()
    if mask.any():
        full.loc[mask, "kickoff_utc"] = pd.to_datetime(full.loc[mask, "Date"], format="%d/%m/%Y")

    full = full.dropna(subset=["FTHG", "FTAG", "kickoff_utc"])
    full["FTHG"] = full["FTHG"].astype(int)
    full["FTAG"] = full["FTAG"].astype(int)
    full = full.sort_values("kickoff_utc").reset_index(drop=True)
    return full


def main() -> None:
    df = load_all()
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    df.to_parquet(OUT_PATH, index=False)
    print(f"Ingested {len(df)} real Premier League matches -> {OUT_PATH}")
    print(f"Date range: {df['kickoff_utc'].min()} -> {df['kickoff_utc'].max()}")
    print(f"Seasons: {sorted(df['season'].unique())}")


if __name__ == "__main__":
    main()
