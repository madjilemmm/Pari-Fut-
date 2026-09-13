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
  btts_prob: number;
  top_scores: ScoreProb[];
  confidence_score: number;
  confidence_note: string;
};

export async function getMatches(limit = 20): Promise<MatchSummary[]> {
  const res = await fetch(`${API_BASE}/matches?limit=${limit}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Donnée indisponible");
  return res.json();
}

export async function getPrediction(matchId: string): Promise<MatchPrediction> {
  const res = await fetch(`${API_BASE}/matches/${matchId}/prediction`, { cache: "no-store" });
  if (!res.ok) throw new Error("Donnée indisponible");
  return res.json();
}
