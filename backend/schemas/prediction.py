from pydantic import BaseModel


class ScoreProb(BaseModel):
    score: str
    prob: float


class MatchPrediction(BaseModel):
    match_id: str
    home_team: str
    away_team: str
    model_version: str
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    home_xg: float
    away_xg: float
    over_2_5_prob: float | None
    btts_prob: float | None
    top_scores: list[ScoreProb]
    confidence_score: float
    confidence_note: str


class MatchSummary(BaseModel):
    match_id: str
    home_team: str
    away_team: str
    kickoff_utc: str
    league: str


class ModelPerformance(BaseModel):
    model_version: str
    evaluation_period: str
    n_predictions: int
    log_loss: float
    brier_score: float
    accuracy: float
