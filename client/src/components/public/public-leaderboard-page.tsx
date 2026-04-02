"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchPublicLeaderboard, PublicLeaderboardError } from "../../lib/api";
import type { LeaderboardEntry } from "../../lib/types";
import { useSession } from "../session/session-provider";

type LeaderboardState =
  | { status: "loading"; leaderboard: LeaderboardEntry[]; errorMessage: null }
  | { status: "ready"; leaderboard: LeaderboardEntry[]; errorMessage: null }
  | { status: "error"; leaderboard: LeaderboardEntry[]; errorMessage: string };

export function PublicLeaderboardPage() {
  const { apiBaseUrl, hasHydrated } = useSession();
  const [state, setState] = useState<LeaderboardState>({
    status: "loading",
    leaderboard: [],
    errorMessage: null
  });

  useEffect(() => {
    if (!hasHydrated) return;
    let isActive = true;
    setState({ status: "loading", leaderboard: [], errorMessage: null });
    void fetchPublicLeaderboard(fetch, { apiBaseUrl })
      .then(({ leaderboard }) => {
        if (!isActive) return;
        setState({ status: "ready", leaderboard, errorMessage: null });
      })
      .catch((error: unknown) => {
        if (!isActive) return;
        setState({
          status: "error",
          leaderboard: [],
          errorMessage:
            error instanceof PublicLeaderboardError
              ? error.message
              : "Unable to load the public leaderboard right now."
        });
      });
    return () => { isActive = false; };
  }, [apiBaseUrl, hasHydrated]);

  return (
    <>
      <section className="hero">
        <h2>Public Leaderboard</h2>
        <p>Read-only rankings from the shipped leaderboard route.</p>
        <div className="actions">
          <Link className="button-link secondary" href="/">Back to home</Link>
          <Link className="button-link secondary" href="/matches/completed">Browse completed matches</Link>
        </div>
      </section>

      {state.status === "loading" ? (
        <section className="panel state-card" aria-live="polite" aria-busy="true">
          <strong>Loading public leaderboard</strong>
          <p>Contacting the configured server now.</p>
        </section>
      ) : state.status === "error" ? (
        <section className="panel state-card" role="status">
          <strong>Leaderboard unavailable</strong>
          <p>{state.errorMessage}</p>
        </section>
      ) : state.leaderboard.length === 0 ? (
        <section className="panel state-card" role="status">
          <strong>No public leaderboard rows yet</strong>
          <p>Completed matches have not produced visible standings yet.</p>
        </section>
      ) : (
        <section className="panel panel-section">
          <h2>Standings</h2>
          <ol className="roster-list" aria-label="Leaderboard standings">
            {state.leaderboard.map((entry) => (
              <li key={`${entry.rank}-${entry.competitor_kind}-${entry.display_name}`} className="roster-row">
                {entry.competitor_kind === "human" && entry.human_id ? (
                  <Link className="button-link secondary" href={`/humans/${entry.human_id}`}>
                    {`${entry.rank}. ${entry.display_name}`}
                  </Link>
                ) : entry.competitor_kind === "agent" && entry.agent_id ? (
                  <Link className="button-link secondary" href={`/agents/${entry.agent_id}`}>
                    {`${entry.rank}. ${entry.display_name}`}
                  </Link>
                ) : (
                  <span>{`${entry.rank}. ${entry.display_name}`}</span>
                )}
                <span>{entry.competitor_kind === "human" ? "Human" : "Agent"}</span>
                <span>{`ELO ${entry.elo}`}</span>
                <span>{`${entry.wins}-${entry.losses}-${entry.draws}`}</span>
                <span>{`${entry.matches_played} matches`}</span>
              </li>
            ))}
          </ol>
        </section>
      )}
    </>
  );
}
