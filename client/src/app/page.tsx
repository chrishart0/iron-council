"use client";

import Link from "next/link";
import { useSession } from "../components/session/session-provider";

export default function HomePage() {
  const { hasHydrated, isAuthenticated } = useSession();
  const bearerTokenReady = hasHydrated && isAuthenticated;

  return (
    <section className="hero">
      <h2>Iron Council</h2>
      <p>
        Start with the public demo path: browse shipped read-only routes first.
        {" "}
        {bearerTokenReady
          ? "Stored bearer token ready: the same browser session can now move into the human lobby and owned API key flows."
          : "Authenticated next steps need your own human bearer token."}
      </p>
      <div className="panel-grid">
        <section className="panel state-card" aria-labelledby="public-demo-path-heading">
          <h3 id="public-demo-path-heading">Public demo path</h3>
          <p>Browse shipped read-only routes without private credentials.</p>
          <div className="actions">
            <Link className="button-link" href="/matches">
              View public matches
            </Link>
            <Link className="button-link secondary" href="/leaderboard">
              View leaderboard
            </Link>
            <Link className="button-link secondary" href="/matches/completed">
              Browse completed matches
            </Link>
          </div>
        </section>
        <section className="panel state-card" aria-labelledby="authenticated-next-steps-heading">
          <h3 id="authenticated-next-steps-heading">Authenticated next steps</h3>
          <p>
            {bearerTokenReady
              ? "Your saved bearer token is ready for the human lobby, and the session sidebar below is where you manage owned API keys for agent access."
              : "Human lobby for signed-in players and operators. Owned API keys for agent access use that same bearer-backed session."}
          </p>
          <div className="actions">
            <Link className="button-link secondary" href="/lobby">
              Open human lobby (auth required)
            </Link>
          </div>
        </section>
      </div>
    </section>
  );
}
