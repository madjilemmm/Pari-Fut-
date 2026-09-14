import Link from "next/link";
import type { MatchPrediction, MatchSummary } from "@/lib/api";
import { ProbabilityBar } from "./ProbabilityBar";

function initials(name: string) {
  return name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 3)
    .toUpperCase();
}

function TeamBadge({ name }: { name: string }) {
  return (
    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-terminal-panel2 text-[11px] font-bold text-terminal-text border border-terminal-border">
      {initials(name)}
    </div>
  );
}

export function MatchCard({
  match,
  prediction,
  featured = false,
  loading = false,
}: {
  match: MatchSummary;
  prediction?: MatchPrediction;
  featured?: boolean;
  loading?: boolean;
}) {
  return (
    <Link
      href={`/matches/${match.match_id}`}
      className={`card-hover fade-in block rounded-xl2 border border-terminal-border bg-terminal-panel p-5 ${
        featured ? "ring-1 ring-terminal-accent/30" : ""
      }`}
    >
      <div className="flex items-center justify-between text-xs text-terminal-muted mb-4">
        <span>{match.league}</span>
        <span>{new Date(match.kickoff_utc).toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" })}</span>
      </div>

      <div className="flex items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2 min-w-0">
          <TeamBadge name={match.home_team} />
          <span className="truncate font-medium">{match.home_team}</span>
        </div>
        <span className="text-terminal-muted text-xs shrink-0">vs</span>
        <div className="flex items-center gap-2 min-w-0 flex-row-reverse">
          <TeamBadge name={match.away_team} />
          <span className="truncate font-medium text-right">{match.away_team}</span>
        </div>
      </div>

      {prediction ? (
        <>
          <ProbabilityBar
            homeLabel={match.home_team}
            awayLabel={match.away_team}
            home={prediction.home_win_prob}
            draw={prediction.draw_prob}
            away={prediction.away_win_prob}
          />
          <div className="mt-4 flex items-center justify-between text-xs text-terminal-muted">
            <span>
              xG {prediction.home_xg.toFixed(2)} — {prediction.away_xg.toFixed(2)}
            </span>
            <span>
              Score probable{" "}
              <span className="text-terminal-text font-medium">{prediction.top_scores[0]?.score}</span>
            </span>
            <span>
              Confiance <span className="text-terminal-text font-medium">{prediction.confidence_score}/100</span>
            </span>
          </div>
        </>
      ) : loading ? (
        <div className="skeleton h-14 rounded-lg" />
      ) : (
        <div className="text-xs text-terminal-muted">Cliquer pour voir l&apos;analyse complète</div>
      )}

      <div className="mt-4 text-right text-xs font-medium text-terminal-accent">ANALYSER LE MATCH →</div>
    </Link>
  );
}
