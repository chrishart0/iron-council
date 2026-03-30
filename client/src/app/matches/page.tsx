import Link from "next/link";
import { MatchBrowser } from "../../components/matches/match-browser";
import { PublicMatchesError, fetchPublicMatches } from "../../lib/api";

export const dynamic = "force-dynamic";

export default async function MatchesPage() {
  try {
    const { matches } = await fetchPublicMatches();

    return (
      <main className="shell">
        <section className="hero">
          <h1>Public Matches</h1>
          <p>
            Read-only browse data from the live server. Match actions stay out of
            scope in this first client slice.
          </p>
          <div className="actions">
            <Link className="button-link secondary" href="/">
              Back to home
            </Link>
          </div>
        </section>
        <MatchBrowser matches={matches} />
      </main>
    );
  } catch (error) {
    const message =
      error instanceof PublicMatchesError
        ? error.message
        : "Unable to load public matches right now.";

    return (
      <main className="shell">
        <section className="hero">
          <h1>Public Matches</h1>
          <p>Read-only browse data from the live server.</p>
          <div className="actions">
            <Link className="button-link secondary" href="/">
              Back to home
            </Link>
          </div>
        </section>
        <MatchBrowser errorMessage={message} />
      </main>
    );
  }
}
