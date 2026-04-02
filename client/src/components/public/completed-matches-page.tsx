"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { CompletedMatchesError, fetchCompletedMatches } from "../../lib/api";
import type { CompletedMatchSummary, PublicCompetitorSummary } from "../../lib/types";
import { useSession } from "../session/session-provider";

type CompletedMatchesState =
  | {
      status: "loading";
      matches: CompletedMatchSummary[];
      errorMessage: null;
    }
  | {
      status: "ready";
      matches: CompletedMatchSummary[];
      errorMessage: null;
    }
  | {
      status: "error";
      matches: CompletedMatchSummary[];
      errorMessage: string;
    };

export function CompletedMatchesPage() {
  const { apiBaseUrl, hasHydrated } = useSession();
  const [state, setState] = useState<CompletedMatchesState>({
    status: "loading",
    matches: [],
    errorMessage: null
  });

  useEffect(() => {
    if (!hasHydrated) {
      return;
    }

    let isActive = true;

    setState({
      status: "loading",
      matches: [],
      errorMessage: null
    });

    void fetchCompletedMatches(fetch, { apiBaseUrl })
      .then(({ matches }) => {
        if (!isActive) {
          return;
        }

        setState({
          status: "ready",
          matches,
          errorMessage: null
        });
      })
      .catch((error: unknown) => {
        if (!isActive) {
          return;
        }

        setState({
          status: "error",
          matches: [],
          errorMessage:
            error instanceof CompletedMatchesError
              ? error.message
              : "Unable to load completed matches right now."
        });
      });

    return () => {
      isActive = false;
    };
  }, [apiBaseUrl, hasHydrated]);

  return (
    <>
      <section className="hero">
        <h2>Completed Matches</h2>
        <p>Read-only finished-match summaries from the shipped browse route.</p>
        <div className="actions">
          <Link className="button-link secondary" href="/">
            Back to home
          </Link>
          <Link className="button-link secondary" href="/leaderboard">
            View public leaderboard
          </Link>
        </div>
      </section>

      {state.status === "loading" ? (
        <section className="panel state-card" aria-live="polite" aria-busy="true">
          <strong>Loading completed matches</strong>
          <p>Contacting the configured server now.</p>
        </section>
      ) : state.status === "error" ? (
        <section className="panel state-card" role="status">
          <strong>Completed matches unavailable</strong>
          <p>{state.errorMessage}</p>
        </section>
      ) : state.matches.length === 0 ? (
        <section className="panel state-card" role="status">
          <strong>No completed matches yet</strong>
          <p>No finished matches are available to browse right now.</p>
        </section>
      ) : (
        <section className="panel panel-section">
          <h2>Recent finished games</h2>
          <ul className="roster-list" aria-label="Completed match summaries">
            {state.matches.map((match) => (
              <li key={match.match_id} className="panel panel-section">
                <p>{match.match_id}</p>
                <p>{`Map: ${match.map}`}</p>
                <p>{`Final tick: ${match.final_tick}`}</p>
                <p>{`Players: ${match.player_count}`}</p>
                <p>{`Completed at: ${match.completed_at}`}</p>
                <p>
                  {match.winning_alliance_name === null
                    ? "Winning alliance: None"
                    : `Winning alliance: ${match.winning_alliance_name}`}
                </p>
                <p>
                  {match.winning_player_display_names.length === 0
                    ? "Winning players: None"
                    : `Winning players: ${match.winning_player_display_names.join(", ")}`}
                </p>
                {match.winning_competitors.length > 0 ? (
                  <div>
                    <span>Winning competitor profiles: </span>
                    <CompetitorSummaryList competitors={match.winning_competitors} />
                  </div>
                ) : null}
                <Link className="button-link secondary" href={`/matches/${match.match_id}/history`}>
                  Open replay/history page
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}

function CompetitorSummaryList({ competitors }: { competitors: PublicCompetitorSummary[] }) {
  return (
    <>
      {competitors.map((competitor, index) => (
        <span key={`${competitor.competitor_kind}:${competitor.display_name}:${index}`}>
          {index > 0 ? ", " : null}
          {competitor.agent_id === null ? (
            competitor.display_name
          ) : (
            <Link href={`/agents/${competitor.agent_id}`}>{competitor.display_name}</Link>
          )}
        </span>
      ))}
    </>
  );
}
