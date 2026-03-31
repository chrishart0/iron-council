import { MatchHistoryPage } from "../../../../components/public/match-history-page";

type MatchHistoryPageProps = {
  params: Promise<{
    matchId: string;
  }>;
  searchParams: Promise<{
    tick?: string;
  }>;
};

export default async function MatchHistoryRoutePage({
  params,
  searchParams
}: MatchHistoryPageProps) {
  const { matchId } = await params;
  const resolvedSearchParams = await searchParams;
  const selectedTick = parseSelectedTick(resolvedSearchParams.tick);

  return <MatchHistoryPage matchId={matchId} selectedTick={selectedTick} />;
}

function parseSelectedTick(value: string | undefined): number | null {
  if (value === undefined) {
    return null;
  }

  const tick = Number(value);

  if (!Number.isInteger(tick) || tick < 0) {
    return null;
  }

  return tick;
}
