"use client";

import { useEffect, useState } from "react";
import type { MatchPrediction, MatchSummary } from "@/lib/api";
import { getPrediction } from "@/lib/api";
import { MatchCard } from "./MatchCard";

/**
 * Client-side prediction loading, on purpose: a cold model fit can take
 * 10-15s on the free-tier backend, which exceeds Vercel's serverless
 * function execution limit if done during server rendering. Fetching it
 * from the browser instead has no such limit — the page loads instantly
 * with real match metadata, and the prediction fills in with a skeleton
 * in between. Never a fake "Loading..." — see MatchCard's loading state.
 */
export function LiveMatchCard({ match, featured = false }: { match: MatchSummary; featured?: boolean }) {
  const [prediction, setPrediction] = useState<MatchPrediction | undefined>(undefined);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getPrediction(match.match_id)
      .then((p) => {
        if (!cancelled) setPrediction(p);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [match.match_id]);

  return <MatchCard match={match} prediction={prediction} featured={featured} loading={!failed && !prediction} />;
}
