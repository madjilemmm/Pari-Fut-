"""
Loads the ingested real Premier League matches (data/processed/matches.parquet)
into PostgreSQL: leagues, teams, matches. Idempotent — safe to re-run.
"""
from __future__ import annotations

import os

import pandas as pd
from sqlalchemy import text

from backend.db.connection import engine

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "matches.parquet")


def main() -> None:
    df = pd.read_parquet(DATA_PATH).sort_values("kickoff_utc").reset_index(drop=True)

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO leagues (name, country, external_code)
            VALUES ('Premier League', 'England', 'E0')
            ON CONFLICT (external_code) DO NOTHING
        """))
        league_id = conn.execute(text("SELECT league_id FROM leagues WHERE external_code='E0'")).scalar()

        teams = pd.unique(df[["HomeTeam", "AwayTeam"]].values.ravel())
        for team in teams:
            conn.execute(text("""
                INSERT INTO teams (league_id, name) VALUES (:league_id, :name)
                ON CONFLICT (league_id, name) DO NOTHING
            """), {"league_id": league_id, "name": team})

        team_ids = dict(conn.execute(text(
            "SELECT name, team_id FROM teams WHERE league_id = :league_id"
        ), {"league_id": league_id}).all())

        inserted = 0
        for _, row in df.iterrows():
            result = conn.execute(text("""
                INSERT INTO matches (league_id, season, home_team_id, away_team_id, kickoff_utc,
                                      status, full_time_home_goals, full_time_away_goals,
                                      half_time_home_goals, half_time_away_goals, source)
                VALUES (:league_id, :season, :home_id, :away_id, :kickoff, 'finished',
                        :fthg, :ftag, :hthg, :htag, :source)
                ON CONFLICT (league_id, season, home_team_id, away_team_id, kickoff_utc) DO NOTHING
            """), {
                "league_id": league_id,
                "season": row["season"],
                "home_id": team_ids[row["HomeTeam"]],
                "away_id": team_ids[row["AwayTeam"]],
                "kickoff": row["kickoff_utc"].to_pydatetime(),
                "fthg": int(row["FTHG"]),
                "ftag": int(row["FTAG"]),
                "hthg": int(row["HTHG"]) if pd.notna(row.get("HTHG")) else None,
                "htag": int(row["HTAG"]) if pd.notna(row.get("HTAG")) else None,
                "source": row["source"],
            })
            inserted += result.rowcount

        conn.execute(text("""
            INSERT INTO model_versions (name, description)
            VALUES ('edge_v0.1_poisson', 'Independent Poisson baseline'),
                   ('edge_v0.2_dixon_coles', 'Dixon-Coles with time-decay, xi=0.005 selected via validation')
            ON CONFLICT (name) DO NOTHING
        """))

    print(f"Loaded {len(teams)} teams and {inserted} new matches into PostgreSQL "
          f"(out of {len(df)} total real matches).")


if __name__ == "__main__":
    main()
