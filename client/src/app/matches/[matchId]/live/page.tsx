import { PublicMatchLivePage } from "../../../../components/matches/public-match-live-page";
import { loadBritainMapLayout } from "../../../../lib/britain-map";

type MatchLivePageProps = {
  params: Promise<{
    matchId: string;
  }>;
};

export default async function MatchLivePage({ params }: MatchLivePageProps) {
  const { matchId } = await params;

  return <PublicMatchLivePage matchId={matchId} mapLayout={loadBritainMapLayout()} />;
}
