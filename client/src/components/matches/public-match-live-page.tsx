"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  buildSpectatorMatchWebSocketUrl,
  fetchPublicMatchDetail,
  parseSpectatorMatchEnvelope,
  PublicMatchDetailError
} from "../../lib/api";
import type { PublicMatchDetailResponse, SpectatorMatchEnvelope } from "../../lib/types";
import type { BritainMapLayout } from "../../lib/britain-map";
import { useSession } from "../session/session-provider";
import { MatchLiveView } from "./match-live-view";
import { MatchLiveMap } from "./match-live-map";

type PublicMatchLivePageProps = {
  matchId: string;
  mapLayout: BritainMapLayout;
};

type MatchDetailState =
  | {
      status: "loading";
      match: null;
      errorMessage: null;
    }
  | {
      status: "ready";
      match: PublicMatchDetailResponse;
      errorMessage: null;
    }
  | {
      status: "error";
      match: null;
      errorMessage: string;
    };

type LiveConnectionState =
  | {
      status: "idle" | "connecting";
      envelope: null;
      message: string | null;
    }
  | {
      status: "live";
      envelope: SpectatorMatchEnvelope;
      message: string | null;
    }
  | {
      status: "not_live";
      envelope: SpectatorMatchEnvelope | null;
      message: string;
    };

export function PublicMatchLivePage({ matchId, mapLayout }: PublicMatchLivePageProps) {
  const { apiBaseUrl, hasHydrated } = useSession();
  const [matchState, setMatchState] = useState<MatchDetailState>({
    status: "loading",
    match: null,
    errorMessage: null
  });
  const [liveState, setLiveState] = useState<LiveConnectionState>({
    status: "idle",
    envelope: null,
    message: null
  });

  useEffect(() => {
    if (!hasHydrated) {
      return;
    }

    let isActive = true;

    setMatchState({
      status: "loading",
      match: null,
      errorMessage: null
    });
    setLiveState({
      status: "idle",
      envelope: null,
      message: null
    });

    void fetchPublicMatchDetail(matchId, fetch, { apiBaseUrl })
      .then((match) => {
        if (!isActive) {
          return;
        }

        setMatchState({
          status: "ready",
          match,
          errorMessage: null
        });
      })
      .catch((error: unknown) => {
        if (!isActive) {
          return;
        }

        setMatchState({
          status: "error",
          match: null,
          errorMessage:
            error instanceof PublicMatchDetailError
              ? error.message
              : "Unable to load this public match right now."
        });
      });

    return () => {
      isActive = false;
    };
  }, [apiBaseUrl, hasHydrated, matchId]);

  useEffect(() => {
    if (!hasHydrated || matchState.status !== "ready") {
      return;
    }

    if (matchState.match.status !== "active") {
      setLiveState({
        status: "not_live",
        envelope: null,
        message: `This match is ${matchState.match.status}, so the spectator live page is not active.`
      });
      return;
    }

    const socket = new WebSocket(buildSpectatorMatchWebSocketUrl(matchId, { apiBaseUrl }));
    let hasClosed = false;

    setLiveState({
      status: "connecting",
      envelope: null,
      message: null
    });

    const markUnavailable = () => {
      if (hasClosed) {
        return;
      }

      hasClosed = true;

      setLiveState((currentState) => ({
        status: "not_live",
        envelope: currentState.envelope,
        message:
          currentState.envelope === null
            ? "Live updates are unavailable right now."
            : "Showing the last spectator update. Reconnect to resume live viewing."
      }));
    };

    socket.onmessage = (event) => {
      try {
        const payload = parseSpectatorMatchEnvelope(JSON.parse(event.data));

        setLiveState({
          status: "live",
          envelope: payload,
          message: null
        });
      } catch {
        markUnavailable();
      }
    };

    socket.onerror = () => {
      markUnavailable();
    };

    socket.onclose = () => {
      markUnavailable();
    };

    return () => {
      hasClosed = true;
      socket.close();
    };
  }, [apiBaseUrl, hasHydrated, matchId, matchState]);

  if (matchState.status === "loading") {
    return (
      <>
        <section className="hero">
          <h2>{`Live Match ${matchId}`}</h2>
          <p>Preparing the public spectator live page from the configured server.</p>
        </section>
        <section className="panel state-card" aria-live="polite" aria-busy="true">
          <strong>Loading live match access</strong>
          <p>Waiting for the public match summary before opening the spectator websocket.</p>
        </section>
      </>
    );
  }

  if (matchState.status === "error") {
    return (
      <>
        <section className="hero">
          <h2>{`Live Match ${matchId}`}</h2>
          <p>Read-only spectator updates from the live server.</p>
          <div className="actions">
            <Link className="button-link secondary" href={`/matches/${matchId}`}>
              Back to match detail
            </Link>
          </div>
        </section>
        <section className="panel state-card" role="status">
          <strong>Live updates unavailable</strong>
          <p>{matchState.errorMessage}</p>
        </section>
      </>
    );
  }

  return (
    <>
      <section className="hero">
        <h2>{`Live Match ${matchState.match.match_id}`}</h2>
        <p>Read-only spectator updates over the existing match websocket.</p>
        <div className="actions">
          <Link className="button-link secondary" href={`/matches/${matchState.match.match_id}`}>
            Back to match detail
          </Link>
        </div>
      </section>

      {liveState.status === "connecting" ? (
        <section className="panel state-card" aria-live="polite">
          <strong>Connecting spectator feed</strong>
          <p>Opening the public websocket now.</p>
        </section>
      ) : null}

      {liveState.status === "not_live" ? (
        <section className="panel state-card" role="status">
          <strong>
            {liveState.envelope === null ? "Live updates unavailable" : "Live connection lost"}
          </strong>
          <p>{liveState.message}</p>
        </section>
      ) : null}

      {liveState.envelope === null ? (
        <MatchLiveMap
          mapLayout={mapLayout}
          liveStatus={liveState.status === "not_live" ? "not_live" : "live"}
          tick={null}
          perspective="spectator"
          cities={[]}
          armies={[]}
        />
      ) : null}

      {liveState.envelope !== null ? (
        <MatchLiveView
          envelope={liveState.envelope}
          mapLayout={mapLayout}
          roster={matchState.match.roster}
          liveStatus={liveState.status === "live" ? "live" : "not_live"}
        />
      ) : null}
    </>
  );
}
