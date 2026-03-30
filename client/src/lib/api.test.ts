import { describe, expect, it, vi } from "vitest";
import {
  buildSpectatorMatchWebSocketUrl,
  fetchPublicMatchDetail,
  fetchPublicMatches,
  parseSpectatorMatchEnvelope,
  PublicMatchDetailError,
  PublicMatchesError
} from "./api";

describe("fetchPublicMatches", () => {
  it("returns the compact public browse payload from the existing matches endpoint", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        matches: [
          {
            match_id: "match-alpha",
            status: "active",
            map: "uk-1900",
            tick: 8,
            tick_interval_seconds: 30,
            current_player_count: 3,
            max_player_count: 6,
            open_slot_count: 3
          }
        ]
      })
    });

    await expect(fetchPublicMatches(fetchImpl as unknown as typeof fetch)).resolves.toEqual({
      matches: [
        {
          match_id: "match-alpha",
          status: "active",
          map: "uk-1900",
          tick: 8,
          tick_interval_seconds: 30,
          current_player_count: 3,
          max_player_count: 6,
          open_slot_count: 3
        }
      ]
    });

    expect(fetchImpl).toHaveBeenCalledWith("http://127.0.0.1:8000/api/v1/matches", {
      cache: "no-store",
      headers: {
        accept: "application/json"
      }
    });
  });

  it("prefers an explicit browser session API base URL when provided", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ matches: [] })
    });

    await fetchPublicMatches(fetchImpl as unknown as typeof fetch, {
      apiBaseUrl: "https://session.example/"
    });

    expect(fetchImpl).toHaveBeenCalledWith("https://session.example/api/v1/matches", {
      cache: "no-store",
      headers: {
        accept: "application/json"
      }
    });
  });

  it("uses the baked-in local default when no browser session override exists", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ matches: [] })
    });

    await fetchPublicMatches(fetchImpl as unknown as typeof fetch);

    expect(fetchImpl).toHaveBeenCalledWith("http://127.0.0.1:8000/api/v1/matches", {
      cache: "no-store",
      headers: {
        accept: "application/json"
      }
    });
  });

  it("raises a deterministic error when the server returns a non-success status", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ detail: "internal details that should not leak" })
    });

    await expect(fetchPublicMatches(fetchImpl as unknown as typeof fetch)).rejects.toEqual(
      new PublicMatchesError("Unable to load public matches right now.")
    );
  });

  it("raises a deterministic error when the payload shape is invalid", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ matches: [{ match_id: "broken" }] })
    });

    await expect(fetchPublicMatches(fetchImpl as unknown as typeof fetch)).rejects.toEqual(
      new PublicMatchesError("Unable to load public matches right now.")
    );
  });
});

describe("fetchPublicMatchDetail", () => {
  it("returns the compact public detail payload from the existing match endpoint", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        match_id: "match-alpha",
        status: "paused",
        map: "uk-1900",
        tick: 18,
        tick_interval_seconds: 45,
        current_player_count: 3,
        max_player_count: 6,
        open_slot_count: 3,
        roster: [
          { display_name: "Arthur", competitor_kind: "human" },
          { display_name: "Morgana", competitor_kind: "agent" }
        ]
      })
    });

    await expect(
      fetchPublicMatchDetail("match-alpha", fetchImpl as unknown as typeof fetch)
    ).resolves.toEqual({
      match_id: "match-alpha",
      status: "paused",
      map: "uk-1900",
      tick: 18,
      tick_interval_seconds: 45,
      current_player_count: 3,
      max_player_count: 6,
      open_slot_count: 3,
      roster: [
        { display_name: "Arthur", competitor_kind: "human" },
        { display_name: "Morgana", competitor_kind: "agent" }
      ]
    });

    expect(fetchImpl).toHaveBeenCalledWith("http://127.0.0.1:8000/api/v1/matches/match-alpha", {
      cache: "no-store",
      headers: {
        accept: "application/json"
      }
    });
  });

  it("prefers an explicit browser session API base URL for public detail requests", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        match_id: "match-alpha",
        status: "active",
        map: "uk-1900",
        tick: 8,
        tick_interval_seconds: 30,
        current_player_count: 3,
        max_player_count: 6,
        open_slot_count: 3,
        roster: []
      })
    });

    await fetchPublicMatchDetail("match-alpha", fetchImpl as unknown as typeof fetch, {
      apiBaseUrl: "https://session.example/"
    });

    expect(fetchImpl).toHaveBeenCalledWith("https://session.example/api/v1/matches/match-alpha", {
      cache: "no-store",
      headers: {
        accept: "application/json"
      }
    });
  });

  it("raises a deterministic not-found error when the public API returns match_not_found", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({
        error: {
          code: "match_not_found",
          message: "Match 'missing' was not found."
        }
      })
    });

    await expect(
      fetchPublicMatchDetail("missing", fetchImpl as unknown as typeof fetch)
    ).rejects.toEqual(
      new PublicMatchDetailError(
        "This match is unavailable. It may not exist or may already be completed.",
        "not_found"
      )
    );
  });

  it("raises a deterministic generic detail error when the payload shape is invalid", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        match_id: "broken",
        status: "active",
        roster: [{ display_name: "Arthur" }]
      })
    });

    await expect(
      fetchPublicMatchDetail("broken", fetchImpl as unknown as typeof fetch)
    ).rejects.toEqual(
      new PublicMatchDetailError("Unable to load this public match right now.", "unavailable")
    );
  });
});

describe("spectator realtime helpers", () => {
  it("parses a valid spectator tick update envelope", () => {
    expect(
      parseSpectatorMatchEnvelope({
        type: "tick_update",
        data: {
          match_id: "match-alpha",
          viewer_role: "spectator",
          player_id: null,
          state: {
            match_id: "match-alpha",
            tick: 143,
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
                location: "manchester",
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
              message_id: 2,
              channel: "world",
              sender_id: "player-1",
              recipient_id: null,
              tick: 143,
              content: "War drums."
            }
          ],
          direct_messages: [],
          group_chats: [],
          group_messages: [],
          treaties: [],
          alliances: []
        }
      })
    ).toEqual({
      type: "tick_update",
      data: {
        match_id: "match-alpha",
        viewer_role: "spectator",
        player_id: null,
        state: {
          match_id: "match-alpha",
          tick: 143,
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
              location: "manchester",
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
            message_id: 2,
            channel: "world",
            sender_id: "player-1",
            recipient_id: null,
            tick: 143,
            content: "War drums."
          }
        ],
        direct_messages: [],
        group_chats: [],
        group_messages: [],
        treaties: [],
        alliances: []
      }
    });
  });

  it("rejects malformed spectator realtime payloads deterministically", () => {
    expect(() =>
      parseSpectatorMatchEnvelope({
        type: "tick_update",
        data: {
          match_id: "match-alpha",
          viewer_role: "spectator",
          state: {
            tick: "143"
          }
        }
      })
    ).toThrowError("Unable to parse spectator live match update.");
  });

  it("builds the shipped spectator websocket URL from the configured API base URL", () => {
    expect(
      buildSpectatorMatchWebSocketUrl("match alpha", {
        apiBaseUrl: "https://session.example/"
      })
    ).toBe("wss://session.example/ws/match/match%20alpha?viewer=spectator");
  });

  it("preserves a configured base-path prefix when building the spectator websocket URL", () => {
    expect(
      buildSpectatorMatchWebSocketUrl("match-alpha", { apiBaseUrl: "https://session.example/game-api" })
    ).toBe("wss://session.example/game-api/ws/match/match-alpha?viewer=spectator");
  });
});
