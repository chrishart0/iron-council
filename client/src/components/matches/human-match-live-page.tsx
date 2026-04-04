"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { BritainMapLayout } from "../../lib/britain-map";
import {
  ApiKeyLifecycleError,
  fetchOwnedAgentGuidedSession,
  fetchOwnedApiKeys,
  GuidedAgentControlsError
} from "../../lib/api";
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
  const [ownedActiveAgentIds, setOwnedActiveAgentIds] = useState<string[] | null>(null);
  const [guidedState, setGuidedState] = useState<GuidedSessionState>({
    status: "idle",
    guidedSession: null,
    errorMessage: null,
    agentId: null
  });
  const liveViewerPlayerId = liveState.envelope?.data.player_id ?? null;
  const liveViewerIsHuman = useMemo(() => {
    if (liveViewerPlayerId === null || matchState.status !== "ready") {
      return false;
    }

    return matchState.match.roster.some(
      (row) => row.player_id === liveViewerPlayerId && row.competitor_kind === "human"
    );
  }, [liveViewerPlayerId, matchState]);

  useEffect(() => {
    if (
      !hasHydrated ||
      bearerToken === null ||
      matchState.status !== "ready" ||
      !liveViewerIsHuman
    ) {
      setOwnedActiveAgentIds(null);
      return;
    }

    let isActive = true;
    void fetchOwnedApiKeys(bearerToken, fetch, { apiBaseUrl })
      .then((response) => {
        if (!isActive) {
          return;
        }

        setOwnedActiveAgentIds(
          response.items.filter((item) => item.is_active).map((item) => item.agent_id)
        );
      })
      .catch((error: unknown) => {
        if (!isActive) {
          return;
        }

        if (error instanceof ApiKeyLifecycleError) {
          setOwnedActiveAgentIds([]);
          return;
        }

        setOwnedActiveAgentIds([]);
      });

    return () => {
      isActive = false;
    };
  }, [apiBaseUrl, bearerToken, hasHydrated, liveViewerIsHuman, matchState.status]);

  const guidedAgentId = useMemo(() => {
    if (ownedActiveAgentIds === null || matchState.status !== "ready") {
      return null;
    }

    const ownedAgentIdSet = new Set(ownedActiveAgentIds);
    const matchedAgentIds = matchState.match.roster.flatMap((row) =>
      row.competitor_kind === "agent" &&
      typeof row.agent_id === "string" &&
      row.agent_id.length > 0 &&
      ownedAgentIdSet.has(row.agent_id)
        ? [row.agent_id]
        : []
    );

    return matchedAgentIds[0] ?? null;
  }, [matchState, ownedActiveAgentIds]);

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
