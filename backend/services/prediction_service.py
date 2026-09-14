"""
Serves predictions strictly from real historical data, read from PostgreSQL
(backend/db/schema.sql) — no longer directly from the parquet file. The
parquet remains the source used by jobs/load_matches_to_postgres.py to
populate the DB in the first place.

IMPORTANT — Phase 1 has no live fixtures/odds/injuries provider wired in.
"Matches" exposed by this API are the real historical Premier League matches
already ingested; predicting one always refits the model using ONLY matches
that occurred strictly before its kickoff, so the numbers are the same ones
the walk-forward backtest already validated — nothing here is invented.

Predictions are NOT persisted to the `predictions` table here: the DB
trigger correctly rejects generated_at > kickoff_utc, and since every match
served in Phase 1 is historical (played in the past), a live "now()"
timestamp would always be after kickoff. Backdating it would defeat the
point of the trigger, so persistence is deferred to when a real live/future
fixtures provider exists (Phase 2) — this is a known, documented gap, not a
silent omission.
"""
from __future__ import annotations

import pandas as pd

from backend.db.connection import engine
from ml.models.dixon_coles import DixonColesModel
from ml.models.elo import EloModel
from ml.simulations.monte_carlo import simulate

MODEL_VERSION = "edge_v0.2_dixon_coles"
SELECTED_XI = 0.005  # chosen via validation grid search, see ml/evaluation/backtest_dixon_coles.py

_df: pd.DataFrame | None = None

# The historical dataset is immutable for the lifetime of the process, so the
# fitted model for a given match_id is always the same. Several endpoints
# (predict/why/power-rating) independently needed a Dixon-Coles and/or Elo
# fit for the SAME match — refitting each one from scratch (an L-BFGS-B
# optimization over ~1500 rows) on every request is what was overloading the
# free-tier backend when the frontend fetched several of them concurrently.
# Caching by match_id removes the redundant work without changing any number.
_dc_cache: dict[str, DixonColesModel] = {}
_elo_cache: dict[str, EloModel] = {}


def _fit_dixon_coles_for(match_id: str, history: pd.DataFrame) -> DixonColesModel:
    if match_id not in _dc_cache:
        _dc_cache[match_id] = DixonColesModel.fit(history, xi=SELECTED_XI)
    return _dc_cache[match_id]


def _fit_elo_for(match_id: str, history: pd.DataFrame) -> EloModel:
    if match_id not in _elo_cache:
        _elo_cache[match_id] = EloModel.fit(history)
    return _elo_cache[match_id]



def _load_df() -> pd.DataFrame:
    global _df
    if _df is None:
        query = """
            SELECT m.match_id, ht.name AS "HomeTeam", at.name AS "AwayTeam",
                   m.full_time_home_goals AS "FTHG", m.full_time_away_goals AS "FTAG",
                   m.kickoff_utc, m.season
            FROM matches m
            JOIN teams ht ON ht.team_id = m.home_team_id
            JOIN teams at ON at.team_id = m.away_team_id
            WHERE m.status = 'finished'
            ORDER BY m.kickoff_utc
        """
        try:
            df = pd.read_sql(query, engine)
        except Exception as e:
            raise FileNotFoundError(
                f"Données indisponibles: base PostgreSQL inaccessible ou vide ({e}). "
                "Exécutez jobs/ingest_football_data_csv.py puis jobs/load_matches_to_postgres.py."
            )
        if df.empty:
            raise FileNotFoundError(
                "Données indisponibles: aucune donnée en base. "
                "Exécutez jobs/ingest_football_data_csv.py puis jobs/load_matches_to_postgres.py."
            )
        df["kickoff_utc"] = pd.to_datetime(df["kickoff_utc"])
        df["match_id"] = df["match_id"].astype(str)
        _df = df
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

    model = _fit_dixon_coles_for(match_id, history)
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


_FULL_HISTORY_DC_CACHE: DixonColesModel | None = None
_FULL_HISTORY_ELO_CACHE: EloModel | None = None


def predict_upcoming(home_team: str, away_team: str) -> dict:
    """Predicts a genuinely future fixture (from a live fixtures provider),
    using the model fit on the ENTIRE historical dataset — there is no
    kickoff cutoff to respect here since nothing in our dataset is after
    the match (unlike predict_match, which walks forward through history).

    Caveat surfaced via confidence_score: our historical dataset stops in
    May 2025, so this is fit on data up to ~16 months stale relative to the
    2026-2027 season, and newly-promoted clubs have no history in it at all
    (they get neutral/default attack-defense-Elo values, not fabricated ones)."""
    global _FULL_HISTORY_DC_CACHE, _FULL_HISTORY_ELO_CACHE
    df = _load_df()

    if _FULL_HISTORY_DC_CACHE is None:
        _FULL_HISTORY_DC_CACHE = DixonColesModel.fit(df, xi=SELECTED_XI)
    if _FULL_HISTORY_ELO_CACHE is None:
        _FULL_HISTORY_ELO_CACHE = EloModel.fit(df)

    model = _FULL_HISTORY_DC_CACHE
    pred = model.predict(home_team, away_team)

    home_hist = len(df[(df["HomeTeam"] == home_team) | (df["AwayTeam"] == home_team)])
    away_hist = len(df[(df["HomeTeam"] == away_team) | (df["AwayTeam"] == away_team)])
    confidence, note = _confidence_score(home_hist, away_hist)
    if home_hist == 0 or away_hist == 0:
        confidence = round(confidence * 0.4, 1)
        note = (
            "Une des deux équipes n'a aucun historique dans notre base (promue en 2025-2026 ou "
            "renommée) — la prédiction utilise des valeurs neutres par défaut, pas des données inventées. "
            "Confiance fortement réduite en conséquence."
        )
    elif home_hist < 40 or away_hist < 40:
        note += " Nos données s'arrêtent en mai 2025 : la saison 2025-2026 n'est pas encore intégrée."

    return {
        "home_team": home_team,
        "away_team": away_team,
        "model_version": MODEL_VERSION,
        "confidence_score": confidence,
        "confidence_note": note,
        **pred,
    }


def simulate_match(match_id: str) -> dict:
    pred = predict_match(match_id)
    result = simulate(pred["home_xg"], pred["away_xg"])
    result["home_team"] = pred["home_team"]
    result["away_team"] = pred["away_team"]
    return result


def form_guide(match_id: str) -> dict:
    """Last 5 finished results before this match's kickoff, for both teams.
    Real results only — 'V'/'N'/'D' (win/draw/loss) from the team's perspective."""
    df = _load_df()
    match = df[df["match_id"] == match_id]
    if match.empty:
        raise KeyError(f"match_id {match_id} introuvable")
    row = match.iloc[0]
    history = df[df["kickoff_utc"] < row["kickoff_utc"]]

    def team_form(team: str) -> dict:
        games = history[(history["HomeTeam"] == team) | (history["AwayTeam"] == team)].tail(5)
        if games.empty:
            return {"results": [], "avg_goals_for": None, "avg_goals_against": None, "note": "Historique insuffisant"}
        results = []
        goals_for, goals_against = [], []
        for _, g in games.iterrows():
            is_home = g["HomeTeam"] == team
            gf = g["FTHG"] if is_home else g["FTAG"]
            ga = g["FTAG"] if is_home else g["FTHG"]
            goals_for.append(int(gf))
            goals_against.append(int(ga))
            results.append("V" if gf > ga else ("D" if gf < ga else "N"))
        return {
            "results": results,
            "avg_goals_for": round(sum(goals_for) / len(goals_for), 2),
            "avg_goals_against": round(sum(goals_against) / len(goals_against), 2),
        }

    return {
        "home_team": row["HomeTeam"],
        "away_team": row["AwayTeam"],
        "home_form": team_form(row["HomeTeam"]),
        "away_form": team_form(row["AwayTeam"]),
    }


def why_match(match_id: str) -> dict:
    """Bullet points derived strictly from real model internals (Dixon-Coles
    attack/defense parameters, Elo ratings, data volume) — never LLM-invented."""
    df = _load_df()
    match = df[df["match_id"] == match_id]
    if match.empty:
        raise KeyError(f"match_id {match_id} introuvable")
    row = match.iloc[0]
    history = df[df["kickoff_utc"] < row["kickoff_utc"]]
    if len(history) < 20:
        raise ValueError("Historique insuffisant pour ce match (Donnée indisponible).")

    model = _fit_dixon_coles_for(match_id, history)
    elo = _fit_elo_for(match_id, history)

    home, away = row["HomeTeam"], row["AwayTeam"]
    home_attack = model.attack.get(home, 0.0)
    away_attack = model.attack.get(away, 0.0)
    home_defense = model.defense.get(home, 0.0)  # lower = better defense
    away_defense = model.defense.get(away, 0.0)
    elo_home, elo_away = elo.rating(home), elo.rating(away)

    home_points, away_points, risks = [], [], []

    if model.home_advantage > 0.05:
        home_points.append("Avantage domicile mesuré positif pour l'équipe recevante")
    if home_attack > away_attack + 0.1:
        home_points.append(f"Meilleure production offensive récente que {away}")
    if elo_home > elo_away + 30:
        home_points.append(f"Rating de force (Elo) supérieur : {elo_home:.0f} vs {elo_away:.0f}")

    if away_attack > home_attack + 0.1:
        away_points.append(f"Meilleure production offensive récente que {home}")
    if elo_away > elo_home + 30:
        away_points.append(f"Rating de force (Elo) supérieur : {elo_away:.0f} vs {elo_home:.0f}")
    if away_defense < home_defense - 0.1:
        away_points.append("Défense plus solide sur les matchs récents")
    if home_defense < away_defense - 0.1:
        home_points.append("Défense plus solide sur les matchs récents")

    home_hist = len(history[(history["HomeTeam"] == home) | (history["AwayTeam"] == home)])
    away_hist = len(history[(history["HomeTeam"] == away) | (history["AwayTeam"] == away)])
    if min(home_hist, away_hist) < 15:
        risks.append("Historique encore limité pour l'une des deux équipes — incertitude plus élevée")
    risks.append("Compositions, blessures et absences non prises en compte (données non connectées)")

    return {
        "home_team": home,
        "away_team": away,
        "home_points": home_points,
        "away_points": away_points,
        "risks": risks,
    }


def power_rating(match_id: str) -> dict:
    """0-100 power rating = percentile rank of each team's current Elo among
    all teams active in the league at that point in time. Derived directly
    from the real Elo model — not a separately invented number."""
    df = _load_df()
    match = df[df["match_id"] == match_id]
    if match.empty:
        raise KeyError(f"match_id {match_id} introuvable")
    row = match.iloc[0]
    history = df[df["kickoff_utc"] < row["kickoff_utc"]]
    elo = _fit_elo_for(match_id, history)

    all_ratings = sorted(elo.ratings.values())
    if len(all_ratings) < 5:
        raise ValueError("Historique insuffisant pour un power rating fiable (Donnée indisponible).")

    def percentile(value: float) -> float:
        below = sum(1 for r in all_ratings if r <= value)
        return round(100 * below / len(all_ratings), 1)

    return {
        "home_team": row["HomeTeam"],
        "away_team": row["AwayTeam"],
        "home_power": percentile(elo.rating(row["HomeTeam"])),
        "away_power": percentile(elo.rating(row["AwayTeam"])),
    }


def elo_ratings_snapshot(as_of_match_id: str) -> dict:
    df = _load_df()
    match = df[df["match_id"] == as_of_match_id]
    if match.empty:
        raise KeyError(f"match_id {as_of_match_id} introuvable")
    row = match.iloc[0]
    history = df[df["kickoff_utc"] < row["kickoff_utc"]]
    elo = _fit_elo_for(as_of_match_id, history)
    return {
        "home_team": row["HomeTeam"],
        "away_team": row["AwayTeam"],
        "home_elo": round(elo.rating(row["HomeTeam"]), 1),
        "away_elo": round(elo.rating(row["AwayTeam"]), 1),
    }
