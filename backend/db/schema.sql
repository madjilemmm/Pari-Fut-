-- Pari Futé — Phase 1 schema (Premier League MVP)
-- Architecture is multi-league from the start; unused tables for players/lineups
-- are created now but not populated until later phases.

CREATE TABLE leagues (
    league_id       SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,      -- e.g. 'Premier League'
    country         TEXT NOT NULL,
    external_code   TEXT UNIQUE                -- e.g. 'E0' (football-data.co.uk code)
);

CREATE TABLE teams (
    team_id         SERIAL PRIMARY KEY,
    league_id       INTEGER REFERENCES leagues(league_id),
    name            TEXT NOT NULL,
    UNIQUE (league_id, name)
);

CREATE TABLE players (
    player_id       SERIAL PRIMARY KEY,
    team_id         INTEGER REFERENCES teams(team_id),
    name            TEXT NOT NULL,
    position        TEXT
);

CREATE TABLE matches (
    match_id        SERIAL PRIMARY KEY,
    league_id       INTEGER NOT NULL REFERENCES leagues(league_id),
    season          TEXT NOT NULL,             -- e.g. '2023-2024'
    home_team_id    INTEGER NOT NULL REFERENCES teams(team_id),
    away_team_id    INTEGER NOT NULL REFERENCES teams(team_id),
    kickoff_utc     TIMESTAMPTZ NOT NULL,
    status          TEXT NOT NULL DEFAULT 'scheduled', -- scheduled|finished|postponed
    full_time_home_goals INTEGER,
    full_time_away_goals INTEGER,
    half_time_home_goals INTEGER,
    half_time_away_goals INTEGER,
    source          TEXT NOT NULL,             -- e.g. 'football-data.co.uk'
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (league_id, season, home_team_id, away_team_id, kickoff_utc)
);

-- Raw + derived per-team, per-match statistics (real-data only; NULL when unavailable)
CREATE TABLE team_match_stats (
    id              SERIAL PRIMARY KEY,
    match_id        INTEGER NOT NULL REFERENCES matches(match_id),
    team_id         INTEGER NOT NULL REFERENCES teams(team_id),
    is_home         BOOLEAN NOT NULL,
    shots           INTEGER,
    shots_on_target INTEGER,
    corners         INTEGER,
    fouls           INTEGER,
    yellow_cards    INTEGER,
    red_cards       INTEGER,
    xg              DOUBLE PRECISION,          -- NULL if provider doesn't supply xG
    xga             DOUBLE PRECISION,
    possession_pct  DOUBLE PRECISION,
    recorded_at     TIMESTAMPTZ NOT NULL,      -- when this stat became known (<= match end)
    UNIQUE (match_id, team_id)
);

CREATE TABLE player_match_stats (
    id              SERIAL PRIMARY KEY,
    match_id        INTEGER NOT NULL REFERENCES matches(match_id),
    player_id       INTEGER NOT NULL REFERENCES players(player_id),
    minutes_played  INTEGER,
    goals           INTEGER,
    assists         INTEGER
);

CREATE TABLE lineups (
    id              SERIAL PRIMARY KEY,
    match_id        INTEGER NOT NULL REFERENCES matches(match_id),
    team_id         INTEGER NOT NULL REFERENCES teams(team_id),
    player_id       INTEGER NOT NULL REFERENCES players(player_id),
    is_starting     BOOLEAN NOT NULL,
    confirmed_at    TIMESTAMPTZ NOT NULL       -- official announcement timestamp
);

CREATE TABLE injuries (
    id              SERIAL PRIMARY KEY,
    player_id       INTEGER NOT NULL REFERENCES players(player_id),
    reported_at     TIMESTAMPTZ NOT NULL,
    expected_return TIMESTAMPTZ,
    description     TEXT
);

CREATE TABLE suspensions (
    id              SERIAL PRIMARY KEY,
    player_id       INTEGER NOT NULL REFERENCES players(player_id),
    match_id        INTEGER REFERENCES matches(match_id),
    reported_at     TIMESTAMPTZ NOT NULL
);

-- Odds: opening + closing, timestamped, per bookmaker; empty until a real provider is wired
CREATE TABLE odds (
    id              SERIAL PRIMARY KEY,
    match_id        INTEGER NOT NULL REFERENCES matches(match_id),
    bookmaker       TEXT NOT NULL,
    market          TEXT NOT NULL,             -- '1x2', 'ou_2.5', 'btts'
    snapshot_type   TEXT NOT NULL,             -- 'opening' | 'closing'
    home_odds       DOUBLE PRECISION,
    draw_odds       DOUBLE PRECISION,
    away_odds       DOUBLE PRECISION,
    recorded_at     TIMESTAMPTZ NOT NULL
);

-- Dynamic team strength rating (Elo etc.), one row per team per as-of date
CREATE TABLE team_ratings (
    id              SERIAL PRIMARY KEY,
    team_id         INTEGER NOT NULL REFERENCES teams(team_id),
    rating_type     TEXT NOT NULL,             -- 'elo'
    rating_value    DOUBLE PRECISION NOT NULL,
    as_of           TIMESTAMPTZ NOT NULL,
    UNIQUE (team_id, rating_type, as_of)
);

CREATE TABLE model_versions (
    model_version_id SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,      -- e.g. 'edge_v0.1_poisson'
    description     TEXT,
    trained_at      TIMESTAMPTZ,
    params          JSONB,
    dataset_ref     TEXT                       -- pointer to the training dataset snapshot
);

-- Immutable snapshot of every feature value available at prediction time
CREATE TABLE feature_snapshots (
    id              SERIAL PRIMARY KEY,
    match_id        INTEGER NOT NULL REFERENCES matches(match_id),
    as_of           TIMESTAMPTZ NOT NULL,      -- strictly <= kickoff_utc
    features        JSONB NOT NULL,
    UNIQUE (match_id, as_of)
);

CREATE TABLE predictions (
    prediction_id   SERIAL PRIMARY KEY,
    match_id        INTEGER NOT NULL REFERENCES matches(match_id),
    model_version_id INTEGER NOT NULL REFERENCES model_versions(model_version_id),
    feature_snapshot_id INTEGER NOT NULL REFERENCES feature_snapshots(id),
    prediction_type TEXT NOT NULL,             -- 'J-7','J-3','J-1','H-6','H-1','lineups_confirmed'
    generated_at    TIMESTAMPTZ NOT NULL,
    home_win_prob   DOUBLE PRECISION NOT NULL,
    draw_prob       DOUBLE PRECISION NOT NULL,
    away_win_prob   DOUBLE PRECISION NOT NULL,
    home_xg         DOUBLE PRECISION NOT NULL,
    away_xg         DOUBLE PRECISION NOT NULL,
    over_2_5_prob   DOUBLE PRECISION,
    btts_prob       DOUBLE PRECISION,
    top_scores      JSONB,                     -- [{"score":"2-1","prob":0.104}, ...]
    confidence_score DOUBLE PRECISION,          -- data-quality score, NOT a win probability
    CHECK (generated_at <= (SELECT kickoff_utc FROM matches m WHERE m.match_id = predictions.match_id))
);

CREATE TABLE prediction_versions (
    id              SERIAL PRIMARY KEY,
    prediction_id   INTEGER NOT NULL REFERENCES predictions(prediction_id),
    superseded_by   INTEGER REFERENCES predictions(prediction_id)
);

CREATE TABLE model_metrics (
    id              SERIAL PRIMARY KEY,
    model_version_id INTEGER NOT NULL REFERENCES model_versions(model_version_id),
    league_id       INTEGER REFERENCES leagues(league_id),
    market          TEXT NOT NULL,             -- '1x2','ou_2.5','btts'
    evaluation_period TEXT NOT NULL,           -- e.g. 'test_2024_2025'
    n_predictions   INTEGER NOT NULL,
    log_loss        DOUBLE PRECISION,
    brier_score     DOUBLE PRECISION,
    calibration_error DOUBLE PRECISION,
    accuracy        DOUBLE PRECISION,
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_matches_kickoff ON matches (kickoff_utc);
CREATE INDEX idx_feature_snapshots_asof ON feature_snapshots (match_id, as_of);
CREATE INDEX idx_predictions_match ON predictions (match_id, generated_at);
