"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getValueBets, ApiError } from "@/lib/api";
import type { ValueBets } from "@/lib/api";
import { ErrorCard, Skeleton } from "@/components/ErrorCard";

function pct(x: number) {
  return `${(x * 100).toFixed(1)}%`;
}

export function ValueBetsClient() {
  const [data, setData] = useState<ValueBets | undefined>();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getValueBets(15)
      .then((d) => !cancelled && setData(d))
      .catch((e) => !cancelled && setError(e instanceof ApiError ? e.message : "Erreur inattendue."));
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <ErrorCard message={error} />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-terminal-accent text-lg">Écarts modèle / marché</h1>
        <p className="text-terminal-muted text-sm mt-1">
          Les matchs où notre modèle et les cotes réelles des bookmakers sont le plus en désaccord.
        </p>
      </div>

      <div className="rounded-xl2 border border-terminal-warn/40 bg-terminal-warn/5 p-5 space-y-2">
        <p className="text-sm font-medium text-terminal-warn">⚠ Ceci n&apos;est pas un conseil de pari.</p>
        <p className="text-xs text-terminal-muted">
          Cette page compare notre modèle statistique <strong>seul</strong> (jamais mélangé aux cotes) à la moyenne
          des cotes réelles du marché. Un grand écart signale un <strong>désaccord</strong>, pas une occasion
          vérifiée : notre propre backtest montre que ce modèle est globalement <strong>moins précis</strong> que
          le marché (voir la page{" "}
          <Link href="/model-performance" className="text-terminal-accent hover:underline">
            Fiabilité
          </Link>
          ). Un écart élevé reflète le plus souvent une erreur du modèle, pas une vraie opportunité. Aucune
          stratégie ici n&apos;a été vérifiée comme rentable. Parier de l&apos;argent comporte un risque réel de
          perte, y compris de tout le montant misé.
        </p>
      </div>

      {!data ? (
        <div className="space-y-3">
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
        </div>
      ) : data.candidates.length === 0 ? (
        <div className="rounded-xl2 border border-dashed border-terminal-border p-6 text-center text-sm text-terminal-muted">
          Aucun écart notable détecté pour le moment (cotes indisponibles ou modèle et marché d&apos;accord).
        </div>
      ) : (
        <div className="space-y-3">
          {data.candidates.map((c, i) => (
            <div key={`${c.fixture_id}-${c.outcome}`} className="rounded-xl2 border border-terminal-border bg-terminal-panel p-5">
              <div className="flex items-center justify-between text-xs text-terminal-muted mb-3">
                <span>
                  {c.home_team} vs {c.away_team}
                </span>
                <span>{new Date(c.kickoff_utc).toLocaleDateString("fr-FR", { day: "2-digit", month: "short" })}</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <div>
                  <div className="text-sm font-semibold">{c.outcome_label}</div>
                  <div className="text-[11px] text-terminal-muted">Cote implicite marché ≈ {c.market_implied_odds}</div>
                </div>
                <div className="flex gap-4 text-center text-xs">
                  <div>
                    <div className="text-terminal-muted mb-0.5">Modèle</div>
                    <div className="font-semibold text-terminal-accent">{pct(c.model_prob)}</div>
                  </div>
                  <div>
                    <div className="text-terminal-muted mb-0.5">Marché</div>
                    <div className="font-semibold">{pct(c.market_prob)}</div>
                  </div>
                  <div>
                    <div className="text-terminal-muted mb-0.5">Écart</div>
                    <div className="font-semibold text-terminal-warn">+{pct(c.edge)}</div>
                  </div>
                </div>
              </div>
              <div className="mt-3 text-[11px] text-terminal-muted">{c.n_bookmakers} bookmakers moyennés</div>
            </div>
          ))}
        </div>
      )}

      <div className="text-center text-[11px] text-terminal-muted pt-2">
        Le jeu d&apos;argent comporte des risques : endettement, dépendance... Pour être aidé, appelez le 09 74 75 13 13
        (appel non surtaxé).
      </div>
    </div>
  );
}
