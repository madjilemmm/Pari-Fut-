import Link from "next/link";
import { getMatches } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  let matches;
  let error: string | null = null;
  try {
    matches = await getMatches(15);
  } catch {
    error = "Donnée indisponible — impossible de contacter l'API backend.";
  }

  return (
    <div>
      <h1 className="text-terminal-accent text-lg mb-1">Premier League</h1>
      <p className="text-terminal-muted mb-6">
        Phase 1 MVP — matchs historiques réels (football-data.co.uk). Aucun calendrier
        de matchs à venir n&apos;est branché tant qu&apos;un fournisseur de fixtures live
        n&apos;est pas configuré.
      </p>

      {error && <p className="text-terminal-danger">{error}</p>}

      <div className="grid gap-3">
        {matches?.map((m) => (
          <Link
            key={m.match_id}
            href={`/matches/${m.match_id}`}
            className="border border-terminal-border rounded-lg p-4 bg-terminal-panel hover:border-terminal-accent transition"
          >
            <div className="flex justify-between">
              <span>{m.home_team} vs {m.away_team}</span>
              <span className="text-terminal-muted">{new Date(m.kickoff_utc).toLocaleDateString("fr-FR")}</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
