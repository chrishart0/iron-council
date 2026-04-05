import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  makeEnvelope,
  makeHiddenTransitEnvelope,
  makePublicMatchDetailResponse,
} from "./human-match-live-page-fixtures";
import {
  MockWebSocket,
  renderHumanMatchLivePage,
  setStoredSession,
} from "./human-match-live-page-test-helpers";

describe("HumanMatchLivePage connection and shell", () => {
  it("waits for hydration, uses the stored bearer token, and opens the shipped player websocket", async () => {
    setStoredSession({
      apiBaseUrl: "https://hydrated.example/",
      bearerToken: "human-jwt"
    });

    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        match_id: "match-alpha",
        status: "active",
        map: "britain",
        tick: 142,
        tick_interval_seconds: 30,
        current_player_count: 3,
        max_player_count: 5,
        open_slot_count: 2,
        roster: []
      })
    });

    vi.stubGlobal("fetch", fetchSpy);
    renderHumanMatchLivePage();

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
      "wss://hydrated.example/ws/match/match-alpha?viewer=player&token=human-jwt"
    );
  });

  it("renders the player-safe snapshot, identifies the viewed player, and updates on later ticks", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          match_id: "match-alpha",
          status: "active",
          map: "britain",
          tick: 142,
          tick_interval_seconds: 30,
          current_player_count: 3,
          max_player_count: 5,
          open_slot_count: 2,
          roster: []
        })
      })
    );
    setStoredSession();
    renderHumanMatchLivePage();

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitOpen();
    socket?.emitMessage(makeEnvelope(143));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Live player state" })).toBeVisible();
    });

    expect(screen.getByText("player-2")).toBeVisible();
    expect(screen.getByText("War drums.")).toBeVisible();
    expect(screen.getByText("Hold the line.")).toBeVisible();
    expect(screen.getByText("Red Council: Ready.")).toBeVisible();
    expect(screen.getByText("alliance accepted between player-1 and player-2")).toBeVisible();
    expect(screen.getByText("Alliance alliance-red led by player-1")).toBeVisible();
    expect(screen.getByText("Visible enemy army near birmingham")).toBeVisible();
    expect(screen.getByText("Food 263")).toBeVisible();
    const initialMapRegion = screen.getByRole("region", { name: "Britain strategic map" });
    expect(within(initialMapRegion).getByText("Tick 143")).toBeVisible();
    expect(within(initialMapRegion).getByText("Manchester")).toBeVisible();
    expect(within(initialMapRegion).getByText("Owner player-2")).toBeVisible();
    expect(within(initialMapRegion).getByText("Owner hidden")).toBeVisible();
    expect(within(initialMapRegion).getByText("Garrison hidden")).toBeVisible();
    expect(within(initialMapRegion).getByText("player-2 army 5 at Manchester")).toBeVisible();
    expect(within(initialMapRegion).getByText("player-3 army hidden near Birmingham")).toBeVisible();

    socket?.emitMessage(makeEnvelope(144));

    await waitFor(() => {
      expect(screen.getByText("Advance at dawn.")).toBeVisible();
    });

    expect(screen.getByText("Press north.")).toBeVisible();
    expect(screen.getByText("Food 264")).toBeVisible();
    expect(screen.getByText("player-2 at leeds with 5 troops (full)")).toBeVisible();
    const updatedMapRegion = screen.getByRole("region", { name: "Britain strategic map" });
    expect(within(updatedMapRegion).getByText("Tick 144")).toBeVisible();
  });

  it("keeps player transit copy fog-safe when the websocket snapshot hides route details", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => makePublicMatchDetailResponse()
      })
    );
    setStoredSession();
    renderHumanMatchLivePage();

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitOpen();
    socket?.emitMessage(makeHiddenTransitEnvelope());

    expect((await screen.findAllByText("player-3 march in progress • ETA 2 ticks")).length).toBe(2);
    expect(screen.queryByText(/marching .* to .* via/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Transit overlay player-3/i)).not.toBeInTheDocument();
  });

  it("shows a deterministic guard when no stored bearer token exists and preserves the page without opening the socket", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    renderHumanMatchLivePage();

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Live updates unavailable");
    });

    expect(
      screen.getByText("This live player page requires a stored human bearer token before it can connect.")
    ).toBeVisible();
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(MockWebSocket.instances).toHaveLength(0);
  });

  it("shows an inactive state for non-active matches and skips the websocket connection", async () => {
    setStoredSession();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          match_id: "match-alpha",
          status: "paused",
          map: "britain",
          tick: 142,
          tick_interval_seconds: 30,
          current_player_count: 3,
          max_player_count: 5,
          open_slot_count: 2,
          roster: []
        })
      })
    );

    renderHumanMatchLivePage();

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Live updates unavailable");
    });

    expect(screen.getByText("This match is paused, so the authenticated live page is not active.")).toBeVisible();
    expect(MockWebSocket.instances).toHaveLength(0);
    const mapRegion = screen.getByRole("region", { name: "Britain strategic map" });
    expect(within(mapRegion).getByText("Player feed offline")).toBeVisible();
    expect(within(mapRegion).getByText("No live strategic map data is available yet.")).toBeVisible();
  });

  it("preserves the last confirmed snapshot after socket failure", async () => {
    setStoredSession();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => makePublicMatchDetailResponse()
      })
    );

    renderHumanMatchLivePage();

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitOpen();
    socket?.emitMessage(makeEnvelope(143));

    await waitFor(() => {
      expect(screen.getByText("War drums.")).toBeVisible();
    });

    socket?.emitError();

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Live connection lost");
    });

    expect(screen.getByText("Showing the last confirmed player snapshot. Reconnect to resume live updates.")).toBeVisible();
    expect(screen.getByText("War drums.")).toBeVisible();
    expect(screen.getAllByText("Not live").length).toBeGreaterThan(0);
    const mapRegion = screen.getByRole("region", { name: "Britain strategic map" });
    expect(within(mapRegion).getByText("Player feed offline")).toBeVisible();
    expect(within(mapRegion).getByText("Manchester")).toBeVisible();
  });

  it("preserves the route-facing shell and major live sections after the player feed drops", async () => {
    setStoredSession();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => makePublicMatchDetailResponse()
      })
    );

    renderHumanMatchLivePage();

    expect(screen.getByRole("heading", { name: "Live Match match-alpha" })).toBeVisible();

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitOpen();
    socket?.emitMessage(makeEnvelope(144));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Map selection inspector" })).toBeVisible();
    });

    expect(screen.getByRole("heading", { name: "Live player state" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Live messaging" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Live diplomacy" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Order Drafts" })).toBeVisible();
    expect(screen.getByText("Advance at dawn.")).toBeVisible();

    socket?.emitClose();

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Live connection lost");
    });

    expect(screen.getByRole("heading", { name: "Live Match match-alpha" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Live player state" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Map selection inspector" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Live messaging" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Live diplomacy" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Order Drafts" })).toBeVisible();
    expect(screen.getByText("Advance at dawn.")).toBeVisible();
    expect(screen.getByText("Showing the last confirmed player snapshot. Reconnect to resume live updates.")).toBeVisible();
  });

  it("fails closed on invalid player websocket payloads while preserving the last confirmed snapshot", async () => {
    setStoredSession();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => makePublicMatchDetailResponse()
      })
    );

    renderHumanMatchLivePage();

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitOpen();
    socket?.emitMessage(makeEnvelope(143));

    await waitFor(() => {
      expect(screen.getByText("War drums.")).toBeVisible();
    });

    socket?.emitMessage({
      type: "tick_update",
      data: {
        match_id: "match-alpha",
        viewer_role: "player",
        player_id: "player-2",
        state: {
          tick: "broken"
        }
      }
    });

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Live connection lost");
    });

    expect(screen.getByText("War drums.")).toBeVisible();
  });

  it("surfaces the backend websocket auth error envelope instead of the generic unavailable text", async () => {
    setStoredSession();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => makePublicMatchDetailResponse()
      })
    );

    renderHumanMatchLivePage();

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitMessage({
      error: {
        code: "player_auth_mismatch",
        message: "This bearer token does not belong to the requested player."
      }
    });

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Live updates unavailable");
    });

    expect(screen.getByText("This bearer token does not belong to the requested player.")).toBeVisible();
    expect(screen.queryByText("Live updates are unavailable right now.")).not.toBeInTheDocument();
  });

  it("surfaces the not-joined close reason while preserving the last confirmed snapshot", async () => {
    setStoredSession();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => makePublicMatchDetailResponse()
      })
    );

    renderHumanMatchLivePage();

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitOpen();
    socket?.emitMessage(makeEnvelope(143));

    await waitFor(() => {
      expect(screen.getByText("War drums.")).toBeVisible();
    });

    socket?.emitClose("human_not_joined");

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Live connection lost");
    });

    expect(
      screen.getByText("Join this match as a human player before opening the authenticated live page.")
    ).toBeVisible();
    expect(screen.getByText("War drums.")).toBeVisible();
    expect(screen.queryByText("Showing the last confirmed player snapshot. Reconnect to resume live updates.")).not.toBeInTheDocument();
  });
});
