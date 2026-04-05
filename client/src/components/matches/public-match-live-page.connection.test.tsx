import { screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  MockWebSocket,
  renderPublicMatchLivePage,
  setStoredSpectatorSession,
  stubSpectatorFetch
} from "./public-match-live-page-test-helpers";
import {
  makeEnvelope,
  makeMatchSummaryResponse,
  makeRosterRow
} from "./public-match-live-page-fixtures";

describe("PublicMatchLivePage connection lifecycle", () => {
  it("waits for session hydration before connecting to the spectator websocket", async () => {
    setStoredSpectatorSession("https://hydrated.example/");
    const fetchSpy = stubSpectatorFetch();

    renderPublicMatchLivePage();

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    expect(fetchSpy).toHaveBeenCalledWith("https://hydrated.example/api/v1/matches/match-alpha", {
      cache: "no-store",
      headers: {
        accept: "application/json"
      }
    });
    expect(MockWebSocket.instances[0]?.url).toBe(
      "wss://hydrated.example/ws/match/match-alpha?viewer=spectator"
    );
  });

  it("shows an inactive state for non-active matches and skips the websocket connection", async () => {
    stubSpectatorFetch(makeMatchSummaryResponse({ status: "paused" }));

    renderPublicMatchLivePage();

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Live updates unavailable");
    });

    expect(screen.getByText("This match is paused, so the spectator live page is not active.")).toBeVisible();
    expect(MockWebSocket.instances).toHaveLength(0);
    const mapRegion = screen.getByRole("region", { name: "Britain strategic map" });
    expect(within(mapRegion).getByText("Spectator feed offline")).toBeVisible();
    expect(within(mapRegion).getByText("No live strategic map data is available yet.")).toBeVisible();
  });

  it("marks the view as not live after the socket disconnects or errors", async () => {
    stubSpectatorFetch(
      makeMatchSummaryResponse({ roster: [makeRosterRow("player-1", "Arthur", "human")] })
    );

    renderPublicMatchLivePage();

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitOpen();
    socket?.emitMessage(makeEnvelope(143));

    await waitFor(() => {
      expect(screen.getByText("143")).toBeVisible();
    });

    socket?.emitError();

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Live connection lost");
    });

    expect(screen.getByText("Showing the last spectator update. Reconnect to resume live viewing.")).toBeVisible();
    expect(screen.getAllByText("Not live").length).toBeGreaterThan(0);
    expect(
      screen.getByText("World chat is unavailable while the spectator feed is not live.")
    ).toBeVisible();
    expect(
      screen.getByText("Treaty status is unavailable while the spectator feed is not live.")
    ).toBeVisible();
    expect(
      screen.getByText("Alliance membership is unavailable while the spectator feed is not live.")
    ).toBeVisible();
    expect(screen.queryByText("Arthur: War drums.")).not.toBeInTheDocument();
    const mapRegion = screen.getByRole("region", { name: "Britain strategic map" });
    expect(within(mapRegion).getByText("Spectator feed offline")).toBeVisible();
    expect(within(mapRegion).getByText("Birmingham")).toBeVisible();
  });
});
