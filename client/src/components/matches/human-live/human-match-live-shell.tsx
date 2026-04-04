"use client";

import Link from "next/link";
import type { BritainMapLayout } from "../../../lib/britain-map";
import type { GuidedSessionState, LiveConnectionState, MatchDetailState } from "./human-match-live-types";
import { HumanMatchLiveSnapshot } from "./human-match-live-snapshot";
import { MatchLiveMap } from "../match-live-map";

type HumanMatchLiveShellProps = {
  matchId: string;
  mapLayout: BritainMapLayout;
  apiBaseUrl: string;
  bearerToken: string | null;
  matchState: MatchDetailState;
  liveState: LiveConnectionState;
  guidedState: GuidedSessionState;
  refreshGuidedSession: () => void;
};

export function HumanMatchLiveShell({
  matchId,
  mapLayout,
  apiBaseUrl,
  bearerToken,
  matchState,
  liveState,
  guidedState,
  refreshGuidedSession
}: HumanMatchLiveShellProps) {
  const statusPanel =
    matchState.status === "loading" ? (
      <section className="panel state-card" aria-live="polite" aria-busy="true">
        <strong>Loading live match access</strong>
        <p>Waiting for the public match summary before opening the player websocket.</p>
      </section>
    ) : liveState.status === "connecting" ? (
      <section className="panel state-card" aria-live="polite">
        <strong>Connecting player feed</strong>
        <p>Opening the authenticated websocket now.</p>
      </section>
    ) : liveState.status === "not_live" ? (
      <section className="panel state-card" role="status">
        <strong>{liveState.envelope === null ? "Live updates unavailable" : "Live connection lost"}</strong>
        <p>{liveState.message}</p>
      </section>
    ) : null;

  return (
    <>
      <section className="hero">
        <h2>{`Live Match ${matchId}`}</h2>
        <p>Authenticated player-safe updates over the shipped match websocket contract.</p>
        <div className="actions">
          <Link className="button-link secondary" href={`/matches/${matchId}`}>
            Back to match detail
          </Link>
        </div>
      </section>

      {statusPanel}

      {liveState.envelope === null ? (
        <MatchLiveMap
          mapLayout={mapLayout}
          liveStatus={liveState.status === "not_live" ? "not_live" : "live"}
          tick={null}
          perspective="player"
          cities={[]}
          armies={[]}
        />
      ) : null}

      {liveState.envelope !== null ? (
        <HumanMatchLiveSnapshot
          envelope={liveState.envelope}
          mapLayout={mapLayout}
          apiBaseUrl={apiBaseUrl}
          bearerToken={bearerToken}
          liveStatus={liveState.status === "live" ? "live" : "not_live"}
          guidedState={guidedState}
          refreshGuidedSession={refreshGuidedSession}
        />
      ) : null}
    </>
  );
}
