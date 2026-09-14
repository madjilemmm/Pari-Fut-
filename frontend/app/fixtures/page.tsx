import { FixtureDetailClient } from "@/components/FixtureDetailClient";

export default function FixturePage({ searchParams }: { searchParams: { home?: string; away?: string } }) {
  const home = searchParams.home || "";
  const away = searchParams.away || "";
  if (!home || !away) {
    return <p className="text-terminal-danger">Match introuvable.</p>;
  }
  return <FixtureDetailClient home={home} away={away} />;
}
