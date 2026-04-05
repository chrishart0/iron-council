import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  MockWebSocket,
  renderPublicMatchLivePage,
  stubSpectatorFetch
} from "./public-match-live-page-test-helpers";
import {
  makeMatchSummaryResponse,
  makeRosterRow,
  makeTransitEnvelope
} from "./public-match-live-page-fixtures";

describe("PublicMatchLivePage map and transit rendering", () => {
  it("renders spectator transit route and ETA copy from the live websocket snapshot", async () => {
    stubSpectatorFetch(
      makeMatchSummaryResponse({ roster: [makeRosterRow("player-1", "Arthur", "human")] })
    );

    renderPublicMatchLivePage();

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitOpen();
    socket?.emitMessage(makeTransitEnvelope());

    expect(await screen.findByText("Arthur marching on Leeds • ETA 3 ticks")).toBeVisible();
    expect(screen.getByText("Arthur march toward Leeds • ETA 3 ticks")).toBeVisible();
  });
});
