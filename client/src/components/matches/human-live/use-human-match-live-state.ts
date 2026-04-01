"use client";

import { useEffect, useState } from "react";
import {
  buildPlayerMatchWebSocketUrl,
  fetchPublicMatchDetail,
  getPlayerWebSocketCloseMessage,
  parsePlayerMatchEnvelope,
  parseWebSocketApiErrorEnvelope,
  PublicMatchDetailError
} from "../../../lib/api";
import type { MatchDetailState, LiveConnectionState } from "./human-match-live-types";

type UseHumanMatchLiveStateArgs = {
  apiBaseUrl: string;
  bearerToken: string | null;
  hasHydrated: boolean;
  matchId: string;
};

export function useHumanMatchLiveState({
  apiBaseUrl,
  bearerToken,
  hasHydrated,
  matchId
}: UseHumanMatchLiveStateArgs): {
  matchState: MatchDetailState;
  liveState: LiveConnectionState;
} {
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

    if (!bearerToken) {
      setMatchState({
        status: "error",
        match: null,
        errorMessage: "This live player page requires a stored human bearer token before it can connect."
      });
      setLiveState({
        status: "not_live",
        envelope: null,
        message: "This live player page requires a stored human bearer token before it can connect."
      });
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

        const errorMessage =
          error instanceof PublicMatchDetailError
            ? error.message
            : "Unable to load this public match right now.";

        setMatchState({
          status: "error",
          match: null,
          errorMessage
        });
        setLiveState({
          status: "not_live",
          envelope: null,
          message: errorMessage
        });
      });

    return () => {
      isActive = false;
    };
  }, [apiBaseUrl, bearerToken, hasHydrated, matchId]);

  useEffect(() => {
    if (!hasHydrated || !bearerToken || matchState.status !== "ready") {
      return;
    }

    if (matchState.match.status !== "active") {
      setLiveState({
        status: "not_live",
        envelope: null,
        message: `This match is ${matchState.match.status}, so the authenticated live page is not active.`
      });
      return;
    }

    const socket = new WebSocket(buildPlayerMatchWebSocketUrl(matchId, bearerToken, { apiBaseUrl }));
    let hasClosed = false;

    setLiveState({
      status: "connecting",
      envelope: null,
      message: null
    });

    const markUnavailable = (options?: { message?: string | null; reason?: string }) => {
      if (hasClosed) {
        return;
      }

      hasClosed = true;

      setLiveState((currentState) => ({
        status: "not_live",
        envelope: currentState.envelope,
        message:
          options?.message ??
          getPlayerWebSocketCloseMessage(options?.reason ?? "") ??
          (currentState.envelope === null
            ? "Live updates are unavailable right now."
            : "Showing the last confirmed player snapshot. Reconnect to resume live updates.")
      }));
    };

    socket.onmessage = (event) => {
      try {
        const parsedPayload: unknown = JSON.parse(event.data);
        const errorEnvelope = parseWebSocketApiErrorEnvelope(parsedPayload);

        if (errorEnvelope !== null) {
          markUnavailable({ message: errorEnvelope.error.message });
          return;
        }

        const payload = parsePlayerMatchEnvelope(parsedPayload);

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

    socket.onclose = (event) => {
      markUnavailable({ reason: event.reason });
    };

    return () => {
      hasClosed = true;
      socket.close();
    };
  }, [apiBaseUrl, bearerToken, hasHydrated, matchId, matchState]);

  return { matchState, liveState };
}
