import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HumanMatchLivePage } from "./human-match-live-page";
import { SessionProvider } from "../session/session-provider";
import { SESSION_STORAGE_KEY } from "../../lib/session-storage";

class MockWebSocket {
  static instances: MockWebSocket[] = [];

  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  readyState = 0;

  constructor(readonly url: string) {
    MockWebSocket.instances.push(this);
  }

  emitOpen() {
    this.readyState = 1;
    this.onopen?.();
  }

  emitMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent<string>);
  }

  emitError() {
    this.onerror?.();
  }

  emitClose(reason = "") {
    this.readyState = 3;
    this.onclose?.({ reason } as CloseEvent);
  }

  close() {
    this.readyState = 3;
  }
}

function makeEnvelope(tick: number) {
  return {
    type: "tick_update",
    data: {
      match_id: "match-alpha",
      viewer_role: "player" as const,
      player_id: "player-2",
      state: {
        match_id: "match-alpha",
        tick,
        player_id: "player-2",
        resources: {
          food: 120 + tick,
          production: 85,
          money: 200
        },
        cities: {
          manchester: {
            owner: "player-2",
            visibility: "full" as const,
            population: 12,
            resources: {
              food: 3,
              production: 2,
              money: 8
            },
            upgrades: {
              economy: 2,
              military: 1,
              fortification: 0
            },
            garrison: 7,
            building_queue: []
          },
          birmingham: {
            owner: "player-3",
            visibility: "partial" as const,
            population: "unknown" as const,
            resources: "unknown" as const,
            upgrades: "unknown" as const,
            garrison: "unknown" as const,
            building_queue: "unknown" as const
          }
        },
        visible_armies: [
          {
            id: "army-1",
            owner: "player-2",
            visibility: "full" as const,
            troops: 5,
            location: tick === 144 ? "leeds" : "manchester",
            destination: null,
            path: null,
            ticks_remaining: 0
          },
          {
            id: "army-2",
            owner: "player-3",
            visibility: "partial" as const,
            troops: "unknown" as const,
            location: null,
            destination: "birmingham",
            path: "unknown" as const,
            ticks_remaining: 2
          }
        ],
        alliance_id: "alliance-red",
        alliance_members: ["player-1", "player-2"],
        victory: {
          leading_alliance: "alliance-red",
          cities_held: 9,
          threshold: 13,
          countdown_ticks_remaining: 4
        }
      },
      world_messages: [
        {
          message_id: tick,
          channel: "world" as const,
          sender_id: "player-1",
          recipient_id: null,
          tick,
          content: tick === 144 ? "Advance at dawn." : "War drums."
        }
      ],
      direct_messages: [
        {
          message_id: tick + 100,
          channel: "direct" as const,
          sender_id: "player-1",
          recipient_id: "player-2",
          tick,
          content: tick === 144 ? "Press north." : "Hold the line."
        }
      ],
      group_chats: [
        {
          group_chat_id: "council-red",
          name: "Red Council",
          member_ids: ["player-1", "player-2"],
          created_by: "player-1",
          created_tick: 140
        }
      ],
      group_messages: [
        {
          message_id: tick + 200,
          group_chat_id: "council-red",
          sender_id: "player-2",
          tick,
          content: tick === 144 ? "Moving." : "Ready."
        }
      ],
      treaties: [
        {
          treaty_id: 5,
          player_a_id: "player-1",
          player_b_id: "player-2",
          treaty_type: "alliance",
          status: "accepted",
          proposed_by: "player-1",
          proposed_tick: 140,
          signed_tick: 141,
          withdrawn_by: null,
          withdrawn_tick: null
        }
      ],
      alliances: [
        {
          alliance_id: "alliance-red",
          name: "alliance-red",
          leader_id: "player-1",
          formed_tick: 140,
          members: [
            { player_id: "player-1", joined_tick: 140 },
            { player_id: "player-2", joined_tick: 140 }
          ]
        }
      ]
    }
  };
}

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  vi.restoreAllMocks();
  MockWebSocket.instances = [];
});

beforeEach(() => {
  vi.stubGlobal("WebSocket", MockWebSocket);
});

describe("HumanMatchLivePage", () => {
  it("waits for hydration, uses the stored bearer token, and opens the shipped player websocket", async () => {
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "https://hydrated.example/",
        bearerToken: "human-jwt"
      })
    );

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

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" />
      </SessionProvider>
    );

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
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" />
      </SessionProvider>
    );

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

    socket?.emitMessage(makeEnvelope(144));

    await waitFor(() => {
      expect(screen.getByText("Advance at dawn.")).toBeVisible();
    });

    expect(screen.getByText("Press north.")).toBeVisible();
    expect(screen.getByText("Food 264")).toBeVisible();
    expect(screen.getByText("player-2 at leeds with 5 troops (full)")).toBeVisible();
  });

  it("shows a deterministic guard when no stored bearer token exists and preserves the page without opening the socket", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" />
      </SessionProvider>
    );

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
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    const fetchSpy = vi.fn().mockResolvedValue({
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
    });

    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Live updates unavailable");
    });

    expect(screen.getByText("This match is paused, so the authenticated live page is not active.")).toBeVisible();
    expect(MockWebSocket.instances).toHaveLength(0);
  });

  it("preserves the last confirmed snapshot after socket failure", async () => {
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

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

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" />
      </SessionProvider>
    );

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
    expect(screen.getAllByText("Not live")).toHaveLength(1);
  });

  it("fails closed on invalid player websocket payloads while preserving the last confirmed snapshot", async () => {
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

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

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" />
      </SessionProvider>
    );

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
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

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

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];

    socket?.emitMessage({
      error: {
        code: "player_auth_mismatch",
        message: "This bearer token does not belong to the requested player."
      }
    });

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Live updates unavailable");
    });

    expect(
      screen.getByText("This bearer token does not belong to the requested player.")
    ).toBeVisible();
    expect(screen.queryByText("Live updates are unavailable right now.")).not.toBeInTheDocument();
  });

  it("surfaces the not-joined close reason while preserving the last confirmed snapshot", async () => {
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

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

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" />
      </SessionProvider>
    );

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
