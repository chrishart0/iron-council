import Link from "next/link";

type MatchHistoryPageProps = {
  params: Promise<{
    matchId: string;
  }>;
};

export default async function MatchHistoryPage({ params }: MatchHistoryPageProps) {
  const { matchId } = await params;

  return (
    <>
      <section className="hero">
        <h2>Match History</h2>
        <p>Read-only landing surface for the persisted history route.</p>
        <div className="actions">
          <Link className="button-link secondary" href="/matches/completed">
            Back to completed matches
          </Link>
          <Link className="button-link secondary" href="/leaderboard">
            View leaderboard
          </Link>
          <Link className="button-link secondary" href="/">
            Back to home
          </Link>
        </div>
      </section>

      <section className="panel panel-section">
        <h3>Match id</h3>
        <p>{matchId}</p>
        <p>Persisted replay inspection and tick-by-tick browsing ship in the next public replay story.</p>
      </section>
    </>
  );
}
