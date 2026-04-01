"use client";

import type { BritainMapLayout } from "../../lib/britain-map";
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

  return (
    <HumanMatchLiveShell
      matchId={matchId}
      mapLayout={mapLayout}
      apiBaseUrl={apiBaseUrl}
      bearerToken={bearerToken}
      matchState={matchState}
      liveState={liveState}
    />
  );
}
