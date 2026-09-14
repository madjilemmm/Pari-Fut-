import Link from "next/link";
import { getLeagues, getMatches, getModelPerformance, ApiError } from "@/lib/api";
import { LiveMatchCard } from "@/components/LiveMatchCard";
import { ErrorCard, EmptyState } from "@/components/ErrorCard";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  let leagues, matches, modelPerf;
  try {
    // Only the fast, DB-backed metadata is fetched server-side. Predictions
    // load client-side (LiveMatchCard) since a cold model fit can take
    // longer than Vercel's serverless function limit — see that component.
    [leagues, matches, modelPerf] = await Promise.all([getLeagues(), getMatches(3), getModelPerformance()]);
  } catch (e) {
    return <ErrorCard message={e instanceof ApiError ? e.message : "Erreur inattendue."} />;
  }

  const featured = matches[matches.length - 1];
  const others = matches.slice(0, matches.length - 1).reverse();

  return (
    <div className="space-y-10">
      {/* Friendly hero, plain language */}
      <div className="text-center space-y-2 pt-2">
        <h1 className="text-2xl sm:text-3xl font-bold">Le football, traduit en probabilités</h1>
        <p className="text-terminal-muted text-sm max-w-md mx-auto">
          Pas de pronostic magique : un vrai modèle statistique qui a fait ses preuves sur des centaines de matchs.
        </p>
      </div>

      {/* League tabs */}
      <div className="flex gap-2 flex-wrap justify-center">
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

      {/* Honest, plain-language data status — no fake live calendar */}
      <EmptyState
        title="Pas encore de matchs à venir"
        body="Le calendrier de la saison en cours n'est pas encore branché. En attendant, découvrez comment le modèle analyse de vrais matchs récents ci-dessous."
      />

      {/* Featured match */}
      <section>
        <h2 className="text-sm uppercase tracking-wide text-terminal-muted mb-3">Exemple d&apos;analyse</h2>
        <LiveMatchCard match={featured} featured />
      </section>

      {/* Other matches */}
      {others.length > 0 && (
        <section>
          <h2 className="text-sm uppercase tracking-wide text-terminal-muted mb-3">Autres exemples</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {others.map((m) => (
              <LiveMatchCard key={m.match_id} match={m} />
            ))}
          </div>
        </section>
      )}

      {/* Model status, simplified */}
      <section className="rounded-xl2 border border-terminal-border bg-terminal-panel p-6 text-center">
        <div className="text-sm text-terminal-muted mb-1">Le modèle a été testé sur</div>
        <div className="text-3xl font-bold text-terminal-accent">{modelPerf.current_model.n_predictions} matchs</div>
        <div className="text-sm text-terminal-muted mt-1">
          qu&apos;il n&apos;avait jamais vus — avec {(modelPerf.current_model.accuracy * 100).toFixed(0)}% de bons résultats prédits
        </div>
        <Link
          href="/model-performance"
          className="inline-block mt-4 rounded-lg border border-terminal-border px-5 py-2 text-sm hover:border-terminal-accent transition"
        >
          Voir le détail des performances
        </Link>
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
