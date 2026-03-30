import { PublicMatchDetailPage } from "../../../components/matches/public-match-detail-page";

type MatchDetailPageProps = {
  params: Promise<{
    matchId: string;
  }>;
};

export default async function MatchDetailPage({ params }: MatchDetailPageProps) {
  const { matchId } = await params;

  return <PublicMatchDetailPage matchId={matchId} />;
}
