"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { MatchPrediction, UpcomingFixture } from "@/lib/api";
import { getFixturePrediction } from "@/lib/api";
import { ProbabilityBar } from "./ProbabilityBar";

function initials(name: string) {
  return name.split(" ").map((w) => w[0]).join("").slice(0, 3).toUpperCase();
}

export function LiveFixtureCard({ fixture }: { fixture: UpcomingFixture }) {
  const [prediction, setPrediction] = useState<MatchPrediction | undefined>();
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getFixturePrediction(fixture.home_team, fixture.away_team)
      .then((p) => !cancelled && setPrediction(p))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [fixture.home_team, fixture.away_team]);

  const href = `/fixtures?home=${encodeURIComponent(fixture.home_team)}&away=${encodeURIComponent(fixture.away_team)}`;

  return (
    <Link href={href} className="card-hover fade-in block rounded-xl2 border border-terminal-border bg-terminal-panel p-5">
      <div className="flex items-center justify-between text-xs text-terminal-muted mb-4">
        <span className="text-terminal-accent">À venir</span>
        <span>{new Date(fixture.kickoff_utc).toLocaleDateString("fr-FR", { weekday: "short", day: "2-digit", month: "short" })}</span>
      </div>
      <div className="flex items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-terminal-panel2 text-[11px] font-bold border border-terminal-border">
            {initials(fixture.home_team)}
          </div>
          <span className="truncate font-medium">{fixture.home_team}</span>
        </div>
        <span className="text-terminal-muted text-xs shrink-0">vs</span>
        <div className="flex items-center gap-2 min-w-0 flex-row-reverse">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-terminal-panel2 text-[11px] font-bold border border-terminal-border">
            {initials(fixture.away_team)}
          </div>
          <span className="truncate font-medium text-right">{fixture.away_team}</span>
        </div>
      </div>
      {prediction ? (
        <ProbabilityBar
          homeLabel={fixture.home_team}
          awayLabel={fixture.away_team}
          home={prediction.home_win_prob}
          draw={prediction.draw_prob}
          away={prediction.away_win_prob}
        />
      ) : failed ? (
        <div className="text-xs text-terminal-muted">Cliquer pour voir l&apos;analyse complète</div>
      ) : (
        <div className="skeleton h-14 rounded-lg" />
      )}
      <div className="mt-4 text-right text-xs font-medium text-terminal-accent">ANALYSER LE MATCH →</div>
    </Link>
  );
}
