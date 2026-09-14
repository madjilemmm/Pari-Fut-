import { getPrediction, getWhy, getForm, getPowerRating, ApiError } from "@/lib/api";
import { ProbabilityBar } from "@/components/ProbabilityBar";
import { ErrorCard } from "@/components/ErrorCard";

export const dynamic = "force-dynamic";

function pct(x: number) {
  return `${(x * 100).toFixed(1)}%`;
}

function FormRow({ label, form }: { label: string; form: { results: string[]; avg_goals_for: number | null; avg_goals_against: number | null; note?: string } }) {
  const color = (r: string) => (r === "V" ? "bg-terminal-accent text-black" : r === "D" ? "bg-terminal-danger/80 text-white" : "bg-terminal-muted/40 text-white");
  return (
    <div>
      <div className="text-xs text-terminal-muted mb-1">{label}</div>
      {form.results.length === 0 ? (
        <div className="text-xs text-terminal-muted">{form.note || "Donnée indisponible"}</div>
      ) : (
        <>
          <div className="flex gap-1 mb-1">
            {form.results.map((r, i) => (
              <span key={i} className={`w-6 h-6 flex items-center justify-center rounded text-[11px] font-bold ${color(r)}`}>
                {r}
              </span>
            ))}
          </div>
          <div className="text-[11px] text-terminal-muted">
            {form.avg_goals_for} buts marqués / {form.avg_goals_against} encaissés en moyenne (5 derniers matchs)
          </div>
        </>
      )}
    </div>
  );
}

export default async function MatchPage({ params }: { params: { id: string } }) {
  let pred;
  try {
    pred = await getPrediction(params.id);
  } catch (e) {
    return <ErrorCard message={e instanceof ApiError ? e.message : "Erreur inattendue."} />;
  }

  const [why, form, power] = await Promise.all([
    getWhy(params.id).catch(() => null),
    getForm(params.id).catch(() => null),
    getPowerRating(params.id).catch(() => null),
  ]);

  return (
    <div className="space-y-8 fade-in">
      {/* Header */}
      <div className="text-center">
        <div className="text-[11px] text-terminal-muted uppercase tracking-wide mb-2">Premier League</div>
        <div className="flex items-center justify-center gap-4 sm:gap-8">
          <div className="text-lg sm:text-2xl font-semibold text-right flex-1">{pred.home_team}</div>
          <div className="text-terminal-muted text-sm">vs</div>
          <div className="text-lg sm:text-2xl font-semibold text-left flex-1">{pred.away_team}</div>
        </div>
        <p className="text-terminal-muted text-xs mt-3">
          Modèle : {pred.model_version.includes("dixon") ? "Dixon-Coles v0.2" : pred.model_version} — probabilités
          issues du moteur quantitatif, jamais générées par un LLM.
        </p>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left / main column */}
        <div className="lg:col-span-2 space-y-6">
          <section className="rounded-xl2 border border-terminal-border bg-terminal-panel p-6">
            <h2 className="text-sm uppercase tracking-wide text-terminal-muted mb-4">Prédiction du modèle</h2>
            <ProbabilityBar
              homeLabel={pred.home_team}
              awayLabel={pred.away_team}
              home={pred.home_win_prob}
              draw={pred.draw_prob}
              away={pred.away_win_prob}
            />
          </section>

          <div className="grid sm:grid-cols-3 gap-4">
            <div className="rounded-xl2 border border-terminal-border bg-terminal-panel p-5">
              <div className="text-xs uppercase tracking-wide text-terminal-muted mb-2">Expected Goals</div>
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
            <h2 className="text-sm uppercase tracking-wide text-terminal-muted mb-4">Autres marchés</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
              <div><div className="text-terminal-muted text-xs">Plus de 2,5 buts</div><div className="font-semibold">{pct(pred.over_2_5_prob)}</div></div>
              <div><div className="text-terminal-muted text-xs">Moins de 2,5 buts</div><div className="font-semibold">{pct(pred.under_2_5_prob)}</div></div>
              <div><div className="text-terminal-muted text-xs">Plus de 1,5 buts</div><div className="font-semibold">{pct(pred.over_1_5_prob)}</div></div>
              <div><div className="text-terminal-muted text-xs">Les deux marquent</div><div className="font-semibold">{pct(pred.btts_prob)}</div></div>
              <div><div className="text-terminal-muted text-xs">Clean sheet {pred.home_team}</div><div className="font-semibold">{pct(pred.clean_sheet_home_prob)}</div></div>
              <div><div className="text-terminal-muted text-xs">Clean sheet {pred.away_team}</div><div className="font-semibold">{pct(pred.clean_sheet_away_prob)}</div></div>
            </div>
          </section>

          {why && (why.home_points.length > 0 || why.away_points.length > 0) && (
            <section className="rounded-xl2 border border-terminal-border bg-terminal-panel p-6">
              <h2 className="text-sm uppercase tracking-wide text-terminal-muted mb-4">Pourquoi le modèle pense ça ?</h2>
              <div className="grid sm:grid-cols-2 gap-4 text-sm">
                <div>
                  <div className="text-terminal-accent text-xs font-medium mb-2">Points favorables {why.home_team}</div>
                  <ul className="space-y-1">
                    {why.home_points.map((p, i) => (
                      <li key={i} className="text-terminal-muted">↑ {p}</li>
                    ))}
                    {why.home_points.length === 0 && <li className="text-terminal-muted">—</li>}
                  </ul>
                </div>
                <div>
                  <div className="text-terminal-accent2 text-xs font-medium mb-2">Points favorables {why.away_team}</div>
                  <ul className="space-y-1">
                    {why.away_points.map((p, i) => (
                      <li key={i} className="text-terminal-muted">↑ {p}</li>
                    ))}
                    {why.away_points.length === 0 && <li className="text-terminal-muted">—</li>}
                  </ul>
                </div>
              </div>
              {why.risks.length > 0 && (
                <div className="mt-4 pt-4 border-t border-terminal-border">
                  <div className="text-terminal-warn text-xs font-medium mb-2">Risques / incertitudes</div>
                  <ul className="space-y-1 text-sm">
                    {why.risks.map((r, i) => (
                      <li key={i} className="text-terminal-muted">! {r}</li>
                    ))}
                  </ul>
                </div>
              )}
            </section>
          )}
        </div>

        {/* Right / sidebar column */}
        <div className="space-y-6">
          {form && (
            <section className="rounded-xl2 border border-terminal-border bg-terminal-panel p-6 space-y-4">
              <h2 className="text-sm uppercase tracking-wide text-terminal-muted">Forme récente</h2>
              <FormRow label={form.home_team} form={form.home_form} />
              <FormRow label={form.away_team} form={form.away_form} />
            </section>
          )}

          {power && (
            <section className="rounded-xl2 border border-terminal-border bg-terminal-panel p-6 space-y-3">
              <h2 className="text-sm uppercase tracking-wide text-terminal-muted">Power Rating</h2>
              <div className="text-[11px] text-terminal-muted -mt-2">Percentile du rating Elo parmi les équipes actives</div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span>{power.home_team}</span>
                  <span className="font-semibold">{power.home_power}/100</span>
                </div>
                <div className="h-2 rounded-full bg-terminal-panel2 overflow-hidden">
                  <div className="h-full bg-terminal-accent prob-bar" style={{ width: `${power.home_power}%` }} />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span>{power.away_team}</span>
                  <span className="font-semibold">{power.away_power}/100</span>
                </div>
                <div className="h-2 rounded-full bg-terminal-panel2 overflow-hidden">
                  <div className="h-full bg-terminal-accent2 prob-bar" style={{ width: `${power.away_power}%` }} />
                </div>
              </div>
            </section>
          )}

          <section className="rounded-xl2 border border-dashed border-terminal-border p-6 text-xs text-terminal-muted">
            Cotes de marché, compositions et blessures : donnée indisponible (Phase 1 — aucun fournisseur configuré).
          </section>

          <section className="rounded-xl2 border border-dashed border-terminal-border p-6 text-xs text-terminal-muted">
            Évolution de la prédiction (J-7 → composition) : composant prêt, historique de prédictions pas encore
            enregistré pour ce match.
          </section>
        </div>
      </div>
    </div>
  );
}
