import { HumanMatchLivePage } from "../../../../components/matches/human-match-live-page";

type MatchPlayPageProps = {
  params: Promise<{
    matchId: string;
  }>;
};

export default async function MatchPlayPage({ params }: MatchPlayPageProps) {
  const { matchId } = await params;

  return <HumanMatchLivePage matchId={matchId} />;
}
