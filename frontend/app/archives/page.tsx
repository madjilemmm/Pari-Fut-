import { getMatches, ApiError } from "@/lib/api";
import { MatchCard } from "@/components/MatchCard";
import { ErrorCard } from "@/components/ErrorCard";

export const dynamic = "force-dynamic";

export default async function ArchivesPage() {
  let matches;
  try {
    matches = await getMatches(40);
  } catch (e) {
    return <ErrorCard message={e instanceof ApiError ? e.message : "Erreur inattendue."} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-terminal-accent text-lg">Archives &amp; Backtest</h1>
        <p className="text-terminal-muted text-sm mt-1">
          Matchs historiques réels Premier League (football-data.co.uk, 2021–2025) utilisés pour entraîner et
          valider le modèle. Chaque prédiction est recalculée en n&apos;utilisant que les données antérieures au
          coup d&apos;envoi de ce match — aucune information future n&apos;est utilisée.
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {matches.map((m) => (
          <MatchCard key={m.match_id} match={m} />
        ))}
      </div>
    </div>
  );
}
