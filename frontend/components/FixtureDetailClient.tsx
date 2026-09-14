"use client";

import { useEffect, useState } from "react";
import { getFixturePrediction, ApiError } from "@/lib/api";
import type { MatchPrediction } from "@/lib/api";
import { ProbabilityBar } from "@/components/ProbabilityBar";
import { ErrorCard, Skeleton } from "@/components/ErrorCard";

function pct(x: number) {
  return `${(x * 100).toFixed(1)}%`;
}

export function FixtureDetailClient({ home, away }: { home: string; away: string }) {
  const [pred, setPred] = useState<MatchPrediction | undefined>();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getFixturePrediction(home, away)
      .then((p) => !cancelled && setPred(p))
      .catch((e) => !cancelled && setError(e instanceof ApiError ? e.message : "Erreur inattendue."));
    return () => {
      cancelled = true;
    };
  }, [home, away]);

  if (error) return <ErrorCard message={error} />;

  if (!pred) {
    return (
      <div className="space-y-6">
        <div className="text-center space-y-3">
          <Skeleton className="h-4 w-32 mx-auto" />
          <Skeleton className="h-8 w-72 mx-auto" />
        </div>
        <Skeleton className="h-24" />
        <Skeleton className="h-40" />
      </div>
    );
  }

  return (
    <div className="space-y-8 fade-in">
      <div className="text-center">
        <div className="text-[11px] text-terminal-accent uppercase tracking-wide mb-2">Match à venir · Premier League</div>
        <div className="flex items-center justify-center gap-4 sm:gap-8">
          <div className="text-lg sm:text-2xl font-semibold text-right flex-1">{pred.home_team}</div>
          <div className="text-terminal-muted text-sm">vs</div>
          <div className="text-lg sm:text-2xl font-semibold text-left flex-1">{pred.away_team}</div>
        </div>
      </div>

      <section className="rounded-xl2 border border-terminal-border bg-terminal-panel p-6">
        <h2 className="text-sm uppercase tracking-wide text-terminal-muted mb-4">Qui va gagner ?</h2>
        <ProbabilityBar
          homeLabel={pred.home_team}
          awayLabel={pred.away_team}
          home={pred.home_win_prob}
          draw={pred.draw_prob}
          away={pred.away_win_prob}
        />
      </section>

      {pred.market && (
        <section className="rounded-xl2 border border-terminal-accent/40 bg-terminal-panel p-6">
          <h2 className="text-sm uppercase tracking-wide text-terminal-accent mb-1">
            Cotes réelles du marché intégrées
          </h2>
          <p className="text-[11px] text-terminal-muted mb-4">
            {pred.market.n_bookmakers} bookmaker{pred.market.n_bookmakers > 1 ? "s" : ""} · probabilités mélangées :{" "}
            {Math.round(pred.market.blend_weight_market * 100)}% marché / {Math.round((1 - pred.market.blend_weight_market) * 100)}% notre modèle statistique.
            Notre modèle seul ne bat pas encore le marché (voir page Fiabilité).
          </p>
          <div className="grid grid-cols-3 gap-3 text-center text-xs">
            <div>
              <div className="text-terminal-muted mb-1">{pred.home_team}</div>
              <div className="font-semibold">{pct(pred.market.market_home_prob)}</div>
              {pred.model_only && <div className="text-terminal-muted">(modèle seul : {pct(pred.model_only.home_win_prob)})</div>}
            </div>
            <div>
              <div className="text-terminal-muted mb-1">Nul</div>
              <div className="font-semibold">{pct(pred.market.market_draw_prob)}</div>
              {pred.model_only && <div className="text-terminal-muted">(modèle seul : {pct(pred.model_only.draw_prob)})</div>}
            </div>
            <div>
              <div className="text-terminal-muted mb-1">{pred.away_team}</div>
              <div className="font-semibold">{pct(pred.market.market_away_prob)}</div>
              {pred.model_only && <div className="text-terminal-muted">(modèle seul : {pct(pred.model_only.away_win_prob)})</div>}
            </div>
          </div>
        </section>
      )}

      <div className="grid sm:grid-cols-3 gap-4">
        <div className="rounded-xl2 border border-terminal-border bg-terminal-panel p-5">
          <div className="text-xs uppercase tracking-wide text-terminal-muted mb-2">Buts attendus (xG)</div>
          <div className="text-sm">{pred.home_team}: <span className="font-semibold">{pred.home_xg.toFixed(2)}</span></div>
          <div className="text-sm">{pred.away_team}: <span className="font-semibold">{pred.away_xg.toFixed(2)}</span></div>
        </div>
        <div className="rounded-xl2 border border-terminal-border bg-terminal-panel p-5">
          <div className="text-xs uppercase tracking-wide text-terminal-muted mb-2">Score le plus probable</div>
          <div className="text-2xl font-semibold text-terminal-accent">{pred.top_scores[0]?.score}</div>
          <div className="text-xs text-terminal-muted">{pct(pred.top_scores[0]?.prob ?? 0)}</div>
        </div>
        <div className="rounded-xl2 border border-terminal-border bg-terminal-panel p-5">
          <div className="text-xs uppercase tracking-wide text-terminal-muted mb-2">Confiance</div>
          <div className="text-2xl font-semibold">{pred.confidence_score}/100</div>
          <div className="text-[11px] text-terminal-muted">{pred.confidence_note}</div>
        </div>
      </div>

      <section className="rounded-xl2 border border-terminal-border bg-terminal-panel p-6">
        <h2 className="text-sm uppercase tracking-wide text-terminal-muted mb-4">Scores les plus probables</h2>
        <div className="grid grid-cols-5 gap-2">
          {pred.top_scores.map((s) => (
            <div key={s.score} className="text-center rounded-lg border border-terminal-border p-3">
              <div className="text-lg font-semibold">{s.score}</div>
              <div className="text-xs text-terminal-muted">{pct(s.prob)}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-xl2 border border-terminal-border bg-terminal-panel p-6">
        <h2 className="text-sm uppercase tracking-wide text-terminal-muted mb-4">Autres statistiques</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
          <div><div className="text-terminal-muted text-xs">Plus de 2,5 buts</div><div className="font-semibold">{pct(pred.over_2_5_prob)}</div></div>
          <div><div className="text-terminal-muted text-xs">Moins de 2,5 buts</div><div className="font-semibold">{pct(pred.under_2_5_prob)}</div></div>
          <div><div className="text-terminal-muted text-xs">Les deux marquent</div><div className="font-semibold">{pct(pred.btts_prob)}</div></div>
        </div>
      </section>

      <div className="rounded-xl2 border border-dashed border-terminal-border p-6 text-xs text-terminal-muted">
        Analyse détaillée (forme récente, points forts, power rating) disponible uniquement pour les matchs
        historiques pour l&apos;instant — voir <a href="/archives" className="text-terminal-accent hover:underline">Matchs</a>.
      </div>
    </div>
  );
}
