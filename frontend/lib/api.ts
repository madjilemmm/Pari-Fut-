const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type MatchSummary = {
  match_id: string;
  home_team: string;
  away_team: string;
  kickoff_utc: string;
  league: string;
};

export type ScoreProb = { score: string; prob: number };

export type MatchPrediction = {
  match_id: string;
  home_team: string;
  away_team: string;
  model_version: string;
  home_win_prob: number;
  draw_prob: number;
  away_win_prob: number;
  home_xg: number;
  away_xg: number;
  over_2_5_prob: number;
  under_2_5_prob: number;
  over_1_5_prob: number;
  btts_prob: number;
  clean_sheet_home_prob: number;
  clean_sheet_away_prob: number;
  top_scores: ScoreProb[];
  confidence_score: number;
  confidence_note: string;
};

export type WhyMatch = {
  home_team: string;
  away_team: string;
  home_points: string[];
  away_points: string[];
  risks: string[];
};

export type TeamForm = {
  results: string[];
  avg_goals_for: number | null;
  avg_goals_against: number | null;
  note?: string;
};

export type FormGuide = {
  home_team: string;
  away_team: string;
  home_form: TeamForm;
  away_form: TeamForm;
};

export type PowerRating = {
  home_team: string;
  away_team: string;
  home_power: number;
  away_power: number;
};

export type League = {
  code: string;
  name: string;
  flag: string;
  status: "active" | "coming_soon";
};

export type ModelSummary = {
  model_version: string;
  display_name?: string;
  evaluation_period?: string;
  n_predictions?: number;
  log_loss?: number;
  brier_score?: number;
  accuracy?: number;
  expected_calibration_error?: number;
  status?: string;
  is_current?: boolean;
};

export type ModelPerformance = {
  note: string;
  current_model: {
    display_name: string;
    version: string;
    n_predictions: number;
    accuracy: number;
    log_loss: number;
    brier_score: number;
    evaluation_period: string;
  };
  models: ModelSummary[];
};

export type UpcomingFixture = {
  fixture_id: string;
  home_team: string;
  away_team: string;
  kickoff_utc: string;
  matchday: number | null;
  league: string;
  source: string;
};

export type CalibrationData = {
  model_version: string;
  note: string;
  expected_calibration_error: number;
  n_predictions: number;
  reliability_curve: { predicted: number; observed: number }[];
};

class ApiError extends Error {}

async function fetchJson<T>(path: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  } catch {
    throw new ApiError("Impossible de contacter le serveur d'analyse.");
  }
  if (!res.ok) {
    if (res.status === 501) throw new ApiError("Donnée indisponible.");
    if (res.status === 404) throw new ApiError("Introuvable.");
    throw new ApiError("Impossible de récupérer l'analyse pour le moment.");
  }
  return res.json();
}

export const getMatches = (limit = 20) => fetchJson<MatchSummary[]>(`/matches?limit=${limit}`);
export const getUpcomingFixtures = (limit = 6) => fetchJson<UpcomingFixture[]>(`/fixtures/upcoming?limit=${limit}`);
export const getFixturePrediction = (home: string, away: string) =>
  fetchJson<MatchPrediction>(`/fixtures/predict?home=${encodeURIComponent(home)}&away=${encodeURIComponent(away)}`);
export const getPrediction = (matchId: string) => fetchJson<MatchPrediction>(`/matches/${matchId}/prediction`);
export const getWhy = (matchId: string) => fetchJson<WhyMatch>(`/matches/${matchId}/why`);
export const getForm = (matchId: string) => fetchJson<FormGuide>(`/matches/${matchId}/form`);
export const getPowerRating = (matchId: string) => fetchJson<PowerRating>(`/matches/${matchId}/power-rating`);
export const getLeagues = () => fetchJson<League[]>(`/leagues`);
export const getModelPerformance = () => fetchJson<ModelPerformance>(`/model/performance`);
export const getCalibration = () => fetchJson<CalibrationData>(`/model/calibration`);

export { ApiError };
