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
        <h1 className="text-terminal-accent text-lg">Matchs analysés</h1>
        <p className="text-terminal-muted text-sm mt-1">
          Ces matchs sont réels (Premier League, 2021–2025) et servent à vérifier que le modèle fonctionne bien.
          Le calendrier de la saison en cours (2026-2027) n&apos;est pas encore branché — voir la page d&apos;accueil.
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
