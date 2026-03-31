import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
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

function makePublicMatchDetailResponse() {
  return {
    match_id: "match-alpha",
    status: "active",
    map: "britain",
    tick: 142,
    tick_interval_seconds: 30,
    current_player_count: 3,
    max_player_count: 5,
    open_slot_count: 2,
    roster: []
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

  it("renders boring order drafts after the first live snapshot and allows adding and removing each order type", async () => {
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

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

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" />
      </SessionProvider>
    );

    expect(screen.queryByRole("heading", { name: "Order Drafts" })).not.toBeInTheDocument();

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitOpen();
    socket?.emitMessage(makeEnvelope(143));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Order Drafts" })).toBeVisible();
    });

    fireEvent.click(screen.getByRole("button", { name: "Add movement order" }));
    fireEvent.click(screen.getByRole("button", { name: "Add recruitment order" }));
    fireEvent.click(screen.getByRole("button", { name: "Add upgrade order" }));
    fireEvent.click(screen.getByRole("button", { name: "Add transfer order" }));

    expect(screen.getByLabelText("Movement army ID 1")).toBeVisible();
    expect(screen.getByLabelText("Recruitment city 1")).toBeVisible();
    expect(screen.getByLabelText("Upgrade city 1")).toBeVisible();
    expect(screen.getByLabelText("Transfer destination 1")).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "Remove movement order 1" }));
    fireEvent.click(screen.getByRole("button", { name: "Remove recruitment order 1" }));
    fireEvent.click(screen.getByRole("button", { name: "Remove upgrade order 1" }));
    fireEvent.click(screen.getByRole("button", { name: "Remove transfer order 1" }));

    expect(screen.queryByLabelText("Movement army ID 1")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Recruitment city 1")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Upgrade city 1")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Transfer destination 1")).not.toBeInTheDocument();
  });

  it("submits current draft orders for the current websocket tick, shows accepted confirmation, and clears the draft", async () => {
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "https://hydrated.example/",
        bearerToken: "human-jwt"
      })
    );

    const fetchSpy = vi.fn().mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

      if (url === "https://hydrated.example/api/v1/matches/match-alpha") {
        return {
          ok: true,
          json: async () => makePublicMatchDetailResponse()
        };
      }

      if (url === "https://hydrated.example/api/v1/matches/match-alpha/commands") {
        return {
          ok: true,
          status: 202,
          json: async () => ({
            status: "accepted",
            match_id: "match-alpha",
            player_id: "player-2",
            tick: 144,
            orders: {
              status: "accepted",
              match_id: "match-alpha",
              player_id: "player-2",
              tick: 144,
              submission_index: 3
            },
            messages: [],
            treaties: [],
            alliance: null
          })
        };
      }

      throw new Error(`Unexpected fetch call: ${url} ${init?.method ?? "GET"}`);
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
    socket?.emitMessage(makeEnvelope(144));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Order Drafts" })).toBeVisible();
    });

    fireEvent.click(screen.getByRole("button", { name: "Add movement order" }));
    fireEvent.change(screen.getByLabelText("Movement army ID 1"), {
      target: { value: "army-1" }
    });
    fireEvent.change(screen.getByLabelText("Movement destination 1"), {
      target: { value: "leeds" }
    });

    fireEvent.click(screen.getByRole("button", { name: "Submit drafted orders" }));

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledTimes(2);
    });

    expect(fetchSpy).toHaveBeenNthCalledWith(2, "https://hydrated.example/api/v1/matches/match-alpha/commands", {
      method: "POST",
      cache: "no-store",
      headers: {
        accept: "application/json",
        authorization: "Bearer human-jwt",
        "content-type": "application/json"
      },
      body: JSON.stringify({
        match_id: "match-alpha",
        tick: 144,
        orders: {
          movements: [{ army_id: "army-1", destination: "leeds" }],
          recruitment: [],
          upgrades: [],
          transfers: []
        },
        messages: [],
        treaties: [],
        alliance: null
      })
    });
    expect(screen.getByText("Orders accepted for tick 144 from player-2.")).toBeVisible();
    expect(screen.queryByLabelText("Movement army ID 1")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Movement destination 1")).not.toBeInTheDocument();
  });

  it("blocks incomplete draft rows before submission and preserves the draft for correction", async () => {
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => makePublicMatchDetailResponse()
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
      expect(screen.getByRole("heading", { name: "Order Drafts" })).toBeVisible();
    });

    fireEvent.click(screen.getByRole("button", { name: "Add recruitment order" }));
    fireEvent.change(screen.getByLabelText("Recruitment city 1"), {
      target: { value: "manchester" }
    });

    fireEvent.click(screen.getByRole("button", { name: "Submit drafted orders" }));

    await waitFor(() => {
      expect(screen.getByText("Recruitment order 1 requires city and troops greater than zero.")).toBeVisible();
    });

    expect(screen.getByText("Error code: invalid_order_draft")).toBeVisible();
    expect(screen.getByText("HTTP status: 400")).toBeVisible();
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText("Recruitment city 1")).toHaveValue("manchester");
    expect(screen.getByLabelText("Recruitment troops 1")).toHaveValue(null);
  });

  it("preserves draft rows and shows structured command failure details when submission is rejected", async () => {
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    const fetchSpy = vi.fn().mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

      if (url === "http://127.0.0.1:8000/api/v1/matches/match-alpha") {
        return {
          ok: true,
          json: async () => makePublicMatchDetailResponse()
        };
      }

      if (url === "http://127.0.0.1:8000/api/v1/matches/match-alpha/commands") {
        return {
          ok: false,
          status: 409,
          json: async () => ({
            error: {
              code: "tick_mismatch",
              message: "Orders already closed for tick 143."
            }
          })
        };
      }

      throw new Error(`Unexpected fetch call: ${url} ${init?.method ?? "GET"}`);
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
      expect(screen.getByRole("heading", { name: "Order Drafts" })).toBeVisible();
    });

    fireEvent.click(screen.getByRole("button", { name: "Add transfer order" }));
    fireEvent.change(screen.getByLabelText("Transfer destination 1"), {
      target: { value: "alliance-red" }
    });
    fireEvent.change(screen.getByLabelText("Transfer resource 1"), {
      target: { value: "money" }
    });
    fireEvent.change(screen.getByLabelText("Transfer amount 1"), {
      target: { value: "25" }
    });

    fireEvent.click(screen.getByRole("button", { name: "Submit drafted orders" }));

    await waitFor(() => {
      expect(screen.getByText("Orders already closed for tick 143.")).toBeVisible();
    });

    expect(fetchSpy).toHaveBeenNthCalledWith(2, "http://127.0.0.1:8000/api/v1/matches/match-alpha/commands", {
      method: "POST",
      cache: "no-store",
      headers: {
        accept: "application/json",
        authorization: "Bearer human-jwt",
        "content-type": "application/json"
      },
      body: JSON.stringify({
        match_id: "match-alpha",
        tick: 143,
        orders: {
          movements: [],
          recruitment: [],
          upgrades: [],
          transfers: [{ to: "alliance-red", resource: "money", amount: 25 }]
        },
        messages: [],
        treaties: [],
        alliance: null
      })
    });
    expect(screen.getByText("Error code: tick_mismatch")).toBeVisible();
    expect(screen.getByText("HTTP status: 409")).toBeVisible();
    expect(screen.getByLabelText("Transfer destination 1")).toHaveValue("alliance-red");
    expect(screen.getByLabelText("Transfer resource 1")).toHaveValue("money");
    expect(screen.getByLabelText("Transfer amount 1")).toHaveValue(25);
  });
});
