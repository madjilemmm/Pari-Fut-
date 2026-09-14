import { MatchDetailClient } from "@/components/MatchDetailClient";

export default function MatchPage({ params }: { params: { id: string } }) {
  return <MatchDetailClient matchId={params.id} />;
}
