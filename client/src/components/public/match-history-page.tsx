"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  fetchMatchReplayTick,
  fetchPublicMatchHistory,
  MatchReplayTickError,
  PublicMatchHistoryError
} from "../../lib/api";
import type {
  MatchReplayTickResponse,
  PublicMatchHistoryResponse
} from "../../lib/types";
import { useSession } from "../session/session-provider";

type MatchHistoryPageProps = {
  matchId: string;
  selectedTick: number | null;
};

type MatchHistoryState =
  | {
      status: "loading";
      history: null;
      errorMessage: null;
    }
  | {
      status: "ready";
      history: PublicMatchHistoryResponse;
      errorMessage: null;
    }
  | {
      status: "error";
      history: null;
      errorMessage: string;
    };

type ReplayState =
  | {
      status: "idle";
      replay: null;
      errorMessage: null;
    }
  | {
      status: "loading";
      replay: null;
      errorMessage: null;
    }
  | {
      status: "ready";
      replay: MatchReplayTickResponse;
      errorMessage: null;
    }
  | {
      status: "error";
      replay: null;
      errorMessage: string;
    };

export function MatchHistoryPage({ matchId, selectedTick }: MatchHistoryPageProps) {
  const { apiBaseUrl, hasHydrated } = useSession();
  const [historyState, setHistoryState] = useState<MatchHistoryState>({
    status: "loading",
    history: null,
    errorMessage: null
  });
  const [replayState, setReplayState] = useState<ReplayState>({
    status: "idle",
    replay: null,
    errorMessage: null
  });

  useEffect(() => {
    if (!hasHydrated) {
      return;
    }

    let isActive = true;

    setHistoryState({
      status: "loading",
      history: null,
      errorMessage: null
    });
    setReplayState({
      status: "idle",
      replay: null,
      errorMessage: null
    });

    void fetchPublicMatchHistory(matchId, fetch, { apiBaseUrl })
      .then((history) => {
        if (!isActive) {
          return;
        }

        setHistoryState({
          status: "ready",
          history,
          errorMessage: null
        });
      })
      .catch((error: unknown) => {
        if (!isActive) {
          return;
        }

        setHistoryState({
          status: "error",
          history: null,
          errorMessage:
            error instanceof PublicMatchHistoryError
              ? error.message
              : "Unable to load match history right now."
        });
      });

    return () => {
      isActive = false;
    };
  }, [apiBaseUrl, hasHydrated, matchId]);

  const effectiveTick =
    historyState.status === "ready"
      ? (selectedTick ?? latestRecordedTick(historyState.history))
      : selectedTick;

  useEffect(() => {
    if (!hasHydrated || historyState.status !== "ready" || effectiveTick === null) {
      return;
    }

    let isActive = true;

    setReplayState({
      status: "loading",
      replay: null,
      errorMessage: null
    });

    void fetchMatchReplayTick(matchId, effectiveTick, fetch, { apiBaseUrl })
      .then((replay) => {
        if (!isActive) {
          return;
        }

        setReplayState({
          status: "ready",
          replay,
          errorMessage: null
        });
      })
      .catch((error: unknown) => {
        if (!isActive) {
          return;
        }

        setReplayState({
          status: "error",
          replay: null,
          errorMessage:
            error instanceof MatchReplayTickError
              ? error.message
              : "Unable to load this replay tick right now."
        });
      });

    return () => {
      isActive = false;
    };
  }, [apiBaseUrl, effectiveTick, hasHydrated, historyState, matchId]);

  if (historyState.status === "loading") {
    return (
      <>
        <section className="hero">
          <h2>Match History</h2>
          <p>Read-only persisted replay inspection from the shipped history routes.</p>
          <HistoryActions />
        </section>
        <section className="panel state-card" aria-live="polite" aria-busy="true">
          <strong>Loading match history</strong>
          <p>Contacting the configured server now.</p>
        </section>
      </>
    );
  }

  if (historyState.status === "error") {
    return (
      <>
        <section className="hero">
          <h2>Match History</h2>
          <p>Read-only persisted replay inspection from the shipped history routes.</p>
          <HistoryActions />
        </section>
        <section className="panel state-card" role="status">
          <strong>Match history unavailable</strong>
          <p>{historyState.errorMessage}</p>
        </section>
      </>
    );
  }

  return (
    <>
      <section className="hero">
        <h2>Match History</h2>
        <p>Read-only persisted replay inspection from the shipped history routes.</p>
        <HistoryActions />
      </section>

      <section className="panel panel-section">
        <h3>History metadata</h3>
        <p>{`Match id: ${historyState.history.match_id}`}</p>
        <p>{`Status: ${historyState.history.status}`}</p>
        <p>{`Current tick: ${historyState.history.current_tick}`}</p>
        <p>{`Tick interval seconds: ${historyState.history.tick_interval_seconds}`}</p>
        <p>{`Recorded ticks: ${historyState.history.history.length}`}</p>
        <div>
          <span>Competitors: </span>
          {historyState.history.competitors.length === 0 ? (
            <span>None</span>
          ) : (
            <ul className="roster-list" aria-label="Competitor roster">
              {historyState.history.competitors.map((competitor, index) => (
                <li
                  key={`${competitor.competitor_kind}:${competitor.display_name}:${index}`}
                  className="roster-row"
                >
                  {competitor.agent_id === null ? (
                    competitor.display_name
                  ) : (
                    <Link href={`/agents/${competitor.agent_id}`}>{competitor.display_name}</Link>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <section className="panel panel-section">
        <h3>Tick picker</h3>
        <p>{`Selected tick: ${effectiveTick === null ? "none" : effectiveTick}`}</p>
        {historyState.history.history.length === 0 ? (
          <p>No persisted ticks are available for this match yet.</p>
        ) : (
          <ul className="roster-list" aria-label="Persisted ticks">
            {historyState.history.history.map((entry) => (
              <li key={entry.tick} className="roster-row">
                <Link
                  className="button-link secondary"
                  href={`/matches/${historyState.history.match_id}/history?tick=${entry.tick}`}
                >
                  {`Tick ${entry.tick}`}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      {replayState.status === "loading" ? (
        <section className="panel state-card" aria-live="polite" aria-busy="true">
          <strong>Loading replay tick</strong>
          <p>Reading the selected persisted snapshot now.</p>
        </section>
      ) : replayState.status === "error" ? (
        <section className="panel state-card" role="status">
          <strong>Replay tick unavailable</strong>
          <p>{replayState.errorMessage}</p>
        </section>
      ) : replayState.status === "ready" ? (
        <>
          <ReplayPanel heading="State snapshot" value={replayState.replay.state_snapshot} />
          <ReplayPanel heading="Orders" value={replayState.replay.orders} />
          <ReplayPanel heading="Events" value={replayState.replay.events} />
        </>
      ) : (
        <section className="panel state-card" role="status">
          <strong>No replay tick selected</strong>
          <p>Choose a persisted tick to inspect its stored snapshot, orders, and events.</p>
        </section>
      )}
    </>
  );
}

function latestRecordedTick(history: PublicMatchHistoryResponse): number | null {
  const latestEntry = history.history.at(-1);
  return latestEntry === undefined ? null : latestEntry.tick;
}

function HistoryActions() {
  return (
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
  );
}

function ReplayPanel({
  heading,
  value
}: {
  heading: string;
  value:
    | MatchReplayTickResponse["state_snapshot"]
    | MatchReplayTickResponse["orders"]
    | MatchReplayTickResponse["events"];
}) {
  return (
    <section className="panel panel-section">
      <h3>{heading}</h3>
      <pre>{JSON.stringify(value, null, 2)}</pre>
    </section>
  );
}
