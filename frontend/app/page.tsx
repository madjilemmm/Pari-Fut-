import Link from "next/link";
import { getLeagues, getMatches, getModelPerformance, getPrediction, ApiError } from "@/lib/api";
import { MatchCard } from "@/components/MatchCard";
import { ErrorCard, EmptyState } from "@/components/ErrorCard";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  let leagues, matches, modelPerf;
  try {
    [leagues, matches, modelPerf] = await Promise.all([getLeagues(), getMatches(6), getModelPerformance()]);
  } catch (e) {
    return <ErrorCard message={e instanceof ApiError ? e.message : "Erreur inattendue."} />;
  }

  const featured = matches[matches.length - 1];
  const others = matches.slice(0, matches.length - 1).reverse();

  const [featuredPred, ...otherPreds] = await Promise.all([
    getPrediction(featured.match_id).catch(() => undefined),
    ...others.map((m) => getPrediction(m.match_id).catch(() => undefined)),
  ]);

  return (
    <div className="space-y-10">
      {/* League tabs */}
      <div className="flex gap-2 flex-wrap">
        {leagues.map((l) => (
          <span
            key={l.code}
            className={`rounded-full px-4 py-1.5 text-xs font-medium border ${
              l.status === "active"
                ? "border-terminal-accent text-terminal-accent bg-terminal-accent/10"
                : "border-terminal-border text-terminal-muted"
            }`}
          >
            {l.flag} {l.name}
            {l.status === "coming_soon" && <span className="ml-1.5 opacity-70">— bientôt</span>}
          </span>
        ))}
      </div>

      {/* Live fixtures empty state — honest, no fake calendar */}
      <EmptyState
        title="Prochains matchs"
        body="Le calendrier live n'est pas encore connecté. Les analyses ci-dessous portent sur les matchs historiques déjà ingérés (voir Archives)."
      />

      {/* Featured match */}
      <section>
        <h2 className="text-sm uppercase tracking-wide text-terminal-muted mb-3">Dernier match analysé</h2>
        <MatchCard match={featured} prediction={featuredPred} featured />
      </section>

      {/* Other matches */}
      {others.length > 0 && (
        <section>
          <h2 className="text-sm uppercase tracking-wide text-terminal-muted mb-3">Autres analyses</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {others.map((m, i) => (
              <MatchCard key={m.match_id} match={m} prediction={otherPreds[i]} />
            ))}
          </div>
        </section>
      )}

      {/* Model status */}
      <section className="rounded-xl2 border border-terminal-border bg-terminal-panel p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h2 className="text-sm uppercase tracking-wide text-terminal-muted mb-1">Model Status</h2>
            <div className="text-xl font-semibold">{modelPerf.current_model.display_name} v0.2</div>
            <div className="text-xs text-terminal-muted mt-1">
              {modelPerf.current_model.n_predictions} matchs testés · Log Loss {modelPerf.current_model.log_loss}
            </div>
          </div>
          <Link
            href="/model-performance"
            className="shrink-0 rounded-lg border border-terminal-border px-4 py-2 text-sm hover:border-terminal-accent transition text-center"
          >
            Voir les performances
          </Link>
        </div>
      </section>

      {/* How it works teaser */}
      <section className="text-center">
        <Link href="/comment-ca-marche" className="text-terminal-accent text-sm hover:underline">
          Comment ça marche ? →
        </Link>
      </section>
    </div>
  );
}
