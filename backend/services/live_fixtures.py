"""
Live Premier League fixtures via football-data.org (free tier).

This is a DataProvider-style abstraction on purpose: nothing outside this
module knows the fixtures come from football-data.org specifically, so a
future paid provider (API-Football, etc.) can be swapped in by replacing
this module's implementation without touching the API layer or frontend.

IMPORTANT — season gap: our historical dataset (data/raw/*.csv) runs
2021-2022 through 2024-2025. The 2025-2026 season is NOT in it. Predictions
made for 2026-2027 fixtures below are therefore fit on data that stops
~16 months before the match, and newly-promoted clubs (e.g. Leeds United)
have NO history in our dataset at all — the model falls back to neutral
attack/defense/Elo defaults for them, which is honest (no invented data)
but noticeably less reliable. This is surfaced to the user via the
confidence score and should be fixed by backfilling 2025-2026 results.
"""
from __future__ import annotations

import os

import httpx

FOOTBALL_DATA_BASE = "https://api.football-data.org/v4"

# football-data.org shortName -> our historical dataset's team name
# (football-data.co.uk naming convention). Only entries that actually
# differ are listed; unmapped names pass through unchanged.
# Confirmed against GET /v4/competitions/PL/teams — football-data.org's
# shortName already matches our dataset's naming for most clubs (Arsenal,
# Man City, Man United, Newcastle, Tottenham, ...); only these differ.
NAME_MAP = {
    "Nottingham": "Nott'm Forest",
    "Brighton Hove": "Brighton",
    "Wolverhampton Wanderers": "Wolves",
    "West Bromwich Albion": "West Brom",
}


def _normalize_team_name(short_name: str) -> str:
    return NAME_MAP.get(short_name, short_name)


def get_upcoming_fixtures(limit: int = 10) -> list[dict]:
    token = os.environ.get("FOOTBALL_DATA_API_TOKEN")
    if not token:
        raise RuntimeError(
            "Donnée indisponible: FOOTBALL_DATA_API_TOKEN non configuré. "
            "Ajoutez la clé football-data.org dans les variables d'environnement du backend."
        )

    try:
        resp = httpx.get(
            f"{FOOTBALL_DATA_BASE}/competitions/PL/matches",
            params={"status": "SCHEDULED"},
            headers={"X-Auth-Token": token},
            timeout=10.0,
        )
        resp.raise_for_status()
    except httpx.HTTPError as e:
        raise RuntimeError(f"Donnée indisponible: football-data.org inaccessible ({e}).")

    data = resp.json()
    fixtures = []
    for m in data.get("matches", [])[:limit]:
        fixtures.append({
            "fixture_id": str(m["id"]),
            "home_team": _normalize_team_name(m["homeTeam"]["shortName"] or m["homeTeam"]["name"]),
            "away_team": _normalize_team_name(m["awayTeam"]["shortName"] or m["awayTeam"]["name"]),
            "kickoff_utc": m["utcDate"],
            "matchday": m.get("matchday"),
            "league": "Premier League",
            "source": "football-data.org",
        })
    return fixtures
