"""
Real live Premier League odds via The Odds API (free tier: 500 requests/month).

Used to blend our independent model with the market ("wisdom of crowds"):
Pinnacle-class odds are extremely hard to beat independently (see
ml/evaluation/compare_vs_market.py — our model alone loses on every metric),
but blending model + market typically lands close to the market's own
accuracy, which is the best honestly achievable outcome for a free,
no-insider-data system. This is NOT the same as "beating the market" —
it's incorporating it, and the UI must say so plainly.
"""
from __future__ import annotations

import os

import httpx

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
SPORT_KEY = "soccer_epl"

# The Odds API team names are close to official names; map the handful that
# differ from our dataset's football-data.co.uk-style naming.
NAME_MAP = {
    "Manchester United": "Man United",
    "Manchester City": "Man City",
    "Nottingham Forest": "Nott'm Forest",
    "Wolverhampton Wanderers": "Wolves",
    "Brighton and Hove Albion": "Brighton",
    "Leeds United": "Leeds",
    "West Bromwich Albion": "West Brom",
    "Newcastle United": "Newcastle",
    "Tottenham Hotspur": "Tottenham",
}


def _normalize(name: str) -> str:
    return NAME_MAP.get(name, name)


def get_market_probs(home_team: str, away_team: str) -> dict | None:
    """Returns de-vigged market implied probabilities for a fixture if
    found, or None if unavailable (no key, quota exhausted, match not
    listed yet) — callers must treat None as 'Donnée indisponible', never
    fall back to a guess."""
    api_key = os.environ.get("ODDS_API_KEY")
    if not api_key:
        return None

    try:
        resp = httpx.get(
            f"{ODDS_API_BASE}/sports/{SPORT_KEY}/odds",
            params={"apiKey": api_key, "regions": "eu", "markets": "h2h", "oddsFormat": "decimal"},
            timeout=10.0,
        )
        resp.raise_for_status()
    except httpx.HTTPError:
        return None

    events = resp.json()
    for event in events:
        eh = _normalize(event.get("home_team", ""))
        ea = _normalize(event.get("away_team", ""))
        if eh != home_team or ea != away_team:
            continue

        # Average de-vigged probabilities across all bookmakers offering h2h,
        # rather than picking just one — reduces single-bookmaker noise.
        all_probs = []
        for bookmaker in event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                if market["key"] != "h2h":
                    continue
                outcomes = {o["name"]: o["price"] for o in market["outcomes"]}
                if event["home_team"] not in outcomes or event["away_team"] not in outcomes or "Draw" not in outcomes:
                    continue
                inv_h = 1 / outcomes[event["home_team"]]
                inv_d = 1 / outcomes["Draw"]
                inv_a = 1 / outcomes[event["away_team"]]
                total = inv_h + inv_d + inv_a
                all_probs.append((inv_h / total, inv_d / total, inv_a / total))

        if not all_probs:
            return None
        n = len(all_probs)
        return {
            "home": sum(p[0] for p in all_probs) / n,
            "draw": sum(p[1] for p in all_probs) / n,
            "away": sum(p[2] for p in all_probs) / n,
            "n_bookmakers": n,
        }

    return None
