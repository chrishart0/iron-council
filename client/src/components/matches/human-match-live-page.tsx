"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { BritainMapLayout } from "../../lib/britain-map";
import { fetchOwnedAgentGuidedSession, GuidedAgentControlsError } from "../../lib/api";
import type { GuidedSessionState } from "./human-live/human-match-live-types";
import { useSession } from "../session/session-provider";
import { HumanMatchLiveShell } from "./human-live/human-match-live-shell";
import { useHumanMatchLiveState } from "./human-live/use-human-match-live-state";

type HumanMatchLivePageProps = {
  matchId: string;
  mapLayout: BritainMapLayout;
};

export function HumanMatchLivePage({ matchId, mapLayout }: HumanMatchLivePageProps) {
  const { apiBaseUrl, bearerToken, hasHydrated } = useSession();
  const { matchState, liveState } = useHumanMatchLiveState({
    apiBaseUrl,
    bearerToken,
    hasHydrated,
    matchId
  });
  const [guidedRefreshToken, setGuidedRefreshToken] = useState(0);
  const [guidedState, setGuidedState] = useState<GuidedSessionState>({
    status: "idle",
    guidedSession: null,
    errorMessage: null,
    agentId: null
  });

  const guidedAgentId = useMemo(() => {
    const playerId = liveState.envelope?.data.player_id ?? null;
    if (playerId === null || matchState.status !== "ready") {
      return null;
    }

    const guidedRow = matchState.match.roster.find(
      (row) =>
        row.player_id === playerId &&
        row.competitor_kind === "agent" &&
        typeof row.agent_id === "string" &&
        row.agent_id.length > 0
    );

    return guidedRow?.agent_id ?? null;
  }, [liveState.envelope, matchState]);

  const refreshGuidedSession = useCallback(() => {
    setGuidedRefreshToken((currentValue) => currentValue + 1);
  }, []);
  const currentGuidedTick = liveState.envelope?.data.state.tick ?? null;

  useEffect(() => {
    if (!hasHydrated || bearerToken === null || guidedAgentId === null) {
      setGuidedState({
        status: "idle",
        guidedSession: null,
        errorMessage: null,
        agentId: guidedAgentId
      });
      return;
    }

    let isActive = true;
    setGuidedState({
      status: "loading",
      guidedSession: null,
      errorMessage: null,
      agentId: guidedAgentId
    });

    void fetchOwnedAgentGuidedSession(matchId, guidedAgentId, bearerToken, fetch, { apiBaseUrl })
      .then((guidedSession) => {
        if (!isActive) {
          return;
        }

        setGuidedState({
          status: "ready",
          guidedSession,
          errorMessage: null,
          agentId: guidedAgentId
        });
      })
      .catch((error: unknown) => {
        if (!isActive) {
          return;
        }

        setGuidedState({
          status: "error",
          guidedSession: null,
          errorMessage:
            error instanceof GuidedAgentControlsError
              ? error.message
              : "Unable to load guided agent controls right now.",
          agentId: guidedAgentId
        });
      });

    return () => {
      isActive = false;
    };
  }, [apiBaseUrl, bearerToken, currentGuidedTick, guidedAgentId, guidedRefreshToken, hasHydrated, matchId]);

  return (
    <HumanMatchLiveShell
      matchId={matchId}
      mapLayout={mapLayout}
      apiBaseUrl={apiBaseUrl}
      bearerToken={bearerToken}
      matchState={matchState}
      liveState={liveState}
      guidedState={guidedState}
      refreshGuidedSession={refreshGuidedSession}
    />
  );
}
