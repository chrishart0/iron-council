import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { loadBritainMapLayout } from "../../lib/britain-map";
import { PublicMatchLivePage } from "./public-match-live-page";
import { SessionProvider } from "../session/session-provider";
import { SESSION_STORAGE_KEY } from "../../lib/session-storage";

class MockWebSocket {
  static instances: MockWebSocket[] = [];

  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;
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

  emitClose() {
    this.readyState = 3;
    this.onclose?.();
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
      viewer_role: "spectator" as const,
      player_id: null,
      state: {
        match_id: "match-alpha",
        tick,
        cities: {
          birmingham: {
            owner: "player-1",
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
          }
        },
        armies: [
          {
            id: "army-1",
            owner: "player-2",
            troops: 5,
            location: tick === 143 ? "manchester" : "leeds",
            destination: null,
            path: null,
            ticks_remaining: 0
          }
        ],
        players: {
          "player-1": {
            resources: {
              food: 120,
              production: 85,
              money: 200
            },
            cities_owned: ["birmingham"],
            alliance_id: null,
            is_eliminated: false
          }
        },
        victory: {
          leading_alliance: null,
          cities_held: 1,
          threshold: 13,
          countdown_ticks_remaining: null
        }
      },
      world_messages: [
        {
          message_id: tick,
          channel: "world" as const,
          sender_id: "player-1",
          recipient_id: null,
          tick,
          content: tick === 143 ? "War drums." : "Advance at dawn."
        }
      ],
      direct_messages: [],
      group_chats: [],
      group_messages: [],
      treaties: [
        {
          treaty_id: tick,
          player_a_id: "player-1",
          player_b_id: "player-9",
          treaty_type: "trade",
          status: "active",
          proposed_by: "player-1",
          proposed_tick: tick - 2,
          signed_tick: tick - 1,
          withdrawn_by: null,
          withdrawn_tick: null
        }
      ],
      alliances: [
        {
          alliance_id: "alliance-red",
          name: "Western Accord",
          leader_id: "player-1",
          formed_tick: 120,
          members: [
            { player_id: "player-1", joined_tick: 120 },
            { player_id: "player-9", joined_tick: 121 }
          ]
        }
      ]
    }
  };
}

function makePressureEnvelope() {
  return {
    type: "tick_update",
    data: {
      match_id: "match-alpha",
      viewer_role: "spectator" as const,
      player_id: null,
      state: {
        match_id: "match-alpha",
        tick: 201,
        cities: {
          london: {
            owner: "player-1",
            population: 12,
            resources: { food: 3, production: 2, money: 8 },
            upgrades: { economy: 2, military: 1, fortification: 0 },
            garrison: 7,
            building_queue: []
          },
          york: {
            owner: "player-9",
            population: 12,
            resources: { food: 3, production: 2, money: 8 },
            upgrades: { economy: 2, military: 1, fortification: 0 },
            garrison: 7,
            building_queue: []
          },
          leeds: {
            owner: "player-2",
            population: 12,
            resources: { food: 3, production: 2, money: 8 },
            upgrades: { economy: 2, military: 1, fortification: 0 },
            garrison: 7,
            building_queue: []
          }
        },
        armies: [],
        players: {
          "player-1": {
            resources: { food: 120, production: 85, money: 200 },
            cities_owned: ["london"],
            alliance_id: "alliance-red",
            is_eliminated: false
          },
          "player-2": {
            resources: { food: 120, production: 85, money: 200 },
            cities_owned: ["leeds"],
            alliance_id: null,
            is_eliminated: false
          },
          "player-9": {
            resources: { food: 120, production: 85, money: 200 },
            cities_owned: ["york"],
            alliance_id: "alliance-red",
            is_eliminated: false
          }
        },
        victory: {
          leading_alliance: "alliance-red",
          cities_held: 2,
          threshold: 13,
          countdown_ticks_remaining: 4
        }
      },
      world_messages: [],
      direct_messages: [],
      group_chats: [],
      group_messages: [],
      treaties: [],
      alliances: [
        {
          alliance_id: "alliance-red",
          name: "Western Accord",
          leader_id: "player-1",
          formed_tick: 120,
          members: [
            { player_id: "player-1", joined_tick: 120 },
            { player_id: "player-9", joined_tick: 121 }
          ]
        }
      ]
    }
  };
}

function makeTransitEnvelope() {
  return {
    type: "tick_update",
    data: {
      match_id: "match-alpha",
      viewer_role: "spectator" as const,
      player_id: null,
      state: {
        match_id: "match-alpha",
        tick: 143,
        cities: {
          manchester: {
            owner: "player-1",
            population: 12,
            resources: { food: 3, production: 2, money: 8 },
            upgrades: { economy: 2, military: 1, fortification: 0 },
            garrison: 7,
            building_queue: []
          },
          leeds: {
            owner: "player-1",
            population: 12,
            resources: { food: 3, production: 2, money: 8 },
            upgrades: { economy: 2, military: 1, fortification: 0 },
            garrison: 3,
            building_queue: []
          }
        },
        armies: [
          {
            id: "army-transit",
            owner: "player-1",
            troops: 9,
            location: "manchester",
            destination: "leeds",
            path: ["manchester", "leeds"],
            ticks_remaining: 3
          }
        ],
        players: {
          "player-1": {
            resources: { food: 120, production: 85, money: 200 },
            cities_owned: ["manchester", "leeds"],
            alliance_id: null,
            is_eliminated: false
          }
        },
        victory: {
          leading_alliance: null,
          cities_held: 2,
          threshold: 13,
          countdown_ticks_remaining: null
        }
      },
      world_messages: [],
      direct_messages: [],
      group_chats: [],
      group_messages: [],
      treaties: [],
      alliances: []
    }
  };
}

function makeCollisionEnvelope() {
  return {
    type: "tick_update",
    data: {
      match_id: "match-alpha",
      viewer_role: "spectator" as const,
      player_id: null,
      state: {
        match_id: "match-alpha",
        tick: 202,
        cities: {
          london: {
            owner: "player-1",
            population: 12,
            resources: { food: 3, production: 2, money: 8 },
            upgrades: { economy: 2, military: 1, fortification: 0 },
            garrison: 7,
            building_queue: []
          },
          york: {
            owner: "player-2",
            population: 12,
            resources: { food: 3, production: 2, money: 8 },
            upgrades: { economy: 2, military: 1, fortification: 0 },
            garrison: 7,
            building_queue: []
          }
        },
        armies: [],
        players: {
          "player-1": {
            resources: { food: 120, production: 85, money: 200 },
            cities_owned: ["london"],
            alliance_id: null,
            is_eliminated: false
          },
          "player-2": {
            resources: { food: 120, production: 85, money: 200 },
            cities_owned: ["york"],
            alliance_id: null,
            is_eliminated: false
          }
        },
        victory: {
          leading_alliance: null,
          cities_held: 0,
          threshold: 13,
          countdown_ticks_remaining: null
        }
      },
      world_messages: [],
      direct_messages: [],
      group_chats: [],
      group_messages: [],
      treaties: [],
      alliances: []
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

describe("PublicMatchLivePage", () => {
  it("waits for session hydration before connecting to the spectator websocket", async () => {
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "https://hydrated.example/",
        bearerToken: null
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
        roster: [
          { player_id: "player-1", display_name: "Arthur", competitor_kind: "human" },
          { player_id: "player-2", display_name: "Morgana", competitor_kind: "agent" }
        ]
      })
    });

    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <PublicMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
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
      "wss://hydrated.example/ws/match/match-alpha?viewer=spectator"
    );
  });

  it("renders the initial spectator payload and deterministic tick updates", async () => {
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
        roster: [
          { player_id: "player-1", display_name: "Arthur", competitor_kind: "human" },
          { player_id: "player-2", display_name: "Morgana", competitor_kind: "agent" }
        ]
      })
    });

    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <PublicMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitOpen();
    socket?.emitMessage(makeEnvelope(143));

    await waitFor(() => {
      expect(screen.getByText("143")).toBeVisible();
    });

    expect(screen.getByText("Arthur: War drums.")).toBeVisible();
    expect(screen.getByText("manchester")).toBeVisible();
    const initialMapRegion = screen.getByRole("region", { name: "Britain strategic map" });
    expect(within(initialMapRegion).getByText("Tick 143")).toBeVisible();
    expect(within(initialMapRegion).getByText("Birmingham")).toBeVisible();
    expect(within(initialMapRegion).getByText("Arthur")).toBeVisible();
    expect(within(initialMapRegion).getByText("Garrison 7")).toBeVisible();
    expect(within(initialMapRegion).getByText("Morgana army 5 at Manchester")).toBeVisible();
    expect(screen.getByText("Arthur and player-9 • trade • active")).toBeVisible();
    expect(screen.getByText("Western Accord: Arthur, player-9")).toBeVisible();

    socket?.emitMessage(makeEnvelope(144));

    await waitFor(() => {
      expect(screen.getByText("144")).toBeVisible();
    });

    expect(screen.getByText("Arthur: Advance at dawn.")).toBeVisible();
    expect(screen.getByText("leeds")).toBeVisible();
    const updatedMapRegion = screen.getByRole("region", { name: "Britain strategic map" });
    expect(within(updatedMapRegion).getByText("Tick 144")).toBeVisible();
  });

  it("renders territory pressure and victory context from the shipped websocket payload", async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        match_id: "match-alpha",
        status: "active",
        map: "britain",
        tick: 200,
        tick_interval_seconds: 30,
        current_player_count: 3,
        max_player_count: 5,
        open_slot_count: 2,
        roster: [
          { player_id: "player-1", display_name: "Arthur", competitor_kind: "human" },
          { player_id: "player-2", display_name: "Morgana", competitor_kind: "agent" }
        ]
      })
    });

    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <PublicMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitOpen();
    socket?.emitMessage(makePressureEnvelope());

    await waitFor(() => {
      expect(screen.getByLabelText("Territory pressure")).toBeVisible();
    });

    const pressureBoard = screen.getByLabelText("Territory pressure");
    const pressureRows = within(pressureBoard).getAllByRole("listitem");
    expect(pressureRows[0]).toHaveTextContent("Western Accord");
    expect(pressureRows[0]).toHaveTextContent("2 cities");
    expect(pressureRows[1]).toHaveTextContent("Morgana");
    expect(pressureRows[1]).toHaveTextContent("1 city");
    expect(
      screen.getByText("Western Accord leads the victory race with 2 of 13 cities.")
    ).toBeVisible();
    expect(screen.getByText("Victory countdown: 4 ticks remaining.")).toBeVisible();
  });

  it("renders spectator transit route and ETA copy from the live websocket snapshot", async () => {
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
        roster: [{ player_id: "player-1", display_name: "Arthur", competitor_kind: "human" }]
      })
    });

    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <PublicMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitOpen();
    socket?.emitMessage(makeTransitEnvelope());

    expect(
      await screen.findByText("Arthur marching Manchester to Leeds via Manchester to Leeds • ETA 3 ticks")
    ).toBeVisible();
    expect(screen.getByText("Arthur march Manchester to Leeds • ETA 3 ticks")).toBeVisible();
  });

  it("keeps same-label players separate in the territory pressure section", async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        match_id: "match-alpha",
        status: "active",
        map: "britain",
        tick: 200,
        tick_interval_seconds: 30,
        current_player_count: 2,
        max_player_count: 5,
        open_slot_count: 3,
        roster: [
          { player_id: "player-1", display_name: "Arthur", competitor_kind: "human" },
          { player_id: "player-2", display_name: "Arthur", competitor_kind: "agent" }
        ]
      })
    });

    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <PublicMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitOpen();
    socket?.emitMessage(makeCollisionEnvelope());

    await waitFor(() => {
      expect(screen.getByLabelText("Territory pressure")).toBeVisible();
    });

    const pressureBoard = screen.getByLabelText("Territory pressure");
    const pressureRows = within(pressureBoard).getAllByRole("listitem");
    expect(pressureRows).toHaveLength(2);
    expect(pressureRows[0]).toHaveTextContent("Arthur");
    expect(pressureRows[0]).toHaveTextContent("1 city");
    expect(pressureRows[1]).toHaveTextContent("Arthur");
    expect(pressureRows[1]).toHaveTextContent("1 city");
  });

  it("shows an inactive state for non-active matches and skips the websocket connection", async () => {
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
        roster: [{ player_id: "player-1", display_name: "Arthur", competitor_kind: "human" }]
      })
    });

    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <PublicMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

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
        roster: [{ player_id: "player-1", display_name: "Arthur", competitor_kind: "human" }]
      })
    });

    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <PublicMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

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
