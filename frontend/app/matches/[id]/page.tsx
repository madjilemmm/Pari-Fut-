import { getPrediction } from "@/lib/api";

export const dynamic = "force-dynamic";

function pct(x: number) {
  return `${(x * 100).toFixed(1)}%`;
}

export default async function MatchPage({ params }: { params: { id: string } }) {
  let pred;
  let error: string | null = null;
  try {
    pred = await getPrediction(params.id);
  } catch {
    error = "Donnée indisponible pour ce match.";
  }

  if (error || !pred) {
    return <p className="text-terminal-danger">{error}</p>;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl">
        {pred.home_team} <span className="text-terminal-muted">vs</span> {pred.away_team}
      </h1>
      <p className="text-terminal-muted text-xs">
        Modèle : {pred.model_version} — probabilités issues du moteur quantitatif (Dixon-Coles),
        jamais générées par un LLM.
      </p>

      <section className="border border-terminal-border rounded-lg p-4 bg-terminal-panel">
        <h2 className="text-terminal-accent mb-2">Probabilités 1X2</h2>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div><div className="text-2xl">{pct(pred.home_win_prob)}</div><div className="text-terminal-muted">Domicile</div></div>
          <div><div className="text-2xl">{pct(pred.draw_prob)}</div><div className="text-terminal-muted">Nul</div></div>
          <div><div className="text-2xl">{pct(pred.away_win_prob)}</div><div className="text-terminal-muted">Extérieur</div></div>
        </div>
      </section>

      <section className="border border-terminal-border rounded-lg p-4 bg-terminal-panel">
        <h2 className="text-terminal-accent mb-2">Expected Goals</h2>
        <p>{pred.home_team}: {pred.home_xg.toFixed(2)} xG — {pred.away_team}: {pred.away_xg.toFixed(2)} xG</p>
        <p className="text-terminal-muted mt-1">Over 2.5 buts: {pct(pred.over_2_5_prob)} · BTTS: {pct(pred.btts_prob)}</p>
      </section>

      <section className="border border-terminal-border rounded-lg p-4 bg-terminal-panel">
        <h2 className="text-terminal-accent mb-2">Top 5 scores les plus probables</h2>
        <ul className="grid grid-cols-5 gap-2 text-center">
          {pred.top_scores.map((s) => (
            <li key={s.score} className="border border-terminal-border rounded p-2">
              <div className="text-lg">{s.score}</div>
              <div className="text-terminal-muted">{pct(s.prob)}</div>
            </li>
          ))}
        </ul>
      </section>

      <section className="border border-terminal-border rounded-lg p-4 bg-terminal-panel">
        <h2 className="text-terminal-accent mb-2">AI Confidence Score</h2>
        <div className="text-2xl">{pred.confidence_score}/100</div>
        <p className="text-terminal-muted mt-1">{pred.confidence_note}</p>
      </section>

      <section className="border border-terminal-border rounded-lg p-4 bg-terminal-panel opacity-60">
        <h2 className="text-terminal-muted mb-2">Cotes de marché / Compositions / Blessures</h2>
        <p>Donnée indisponible (Phase 1 — aucun fournisseur configuré).</p>
      </section>
    </div>
  );
}
