import { describe, expect, it, vi } from "vitest";
import {
  buildPlayerMatchWebSocketUrl,
  buildSpectatorMatchWebSocketUrl,
  CompletedMatchesError,
  CommandSubmissionError,
  createMatchLobby,
  DiplomacySubmissionError,
  fetchCompletedMatches,
  fetchMatchReplayTick,
  fetchPublicMatchHistory,
  fetchPublicLeaderboard,
  fetchPublicMatchDetail,
  fetchPublicMatches,
  GroupChatCreateError,
  getPlayerWebSocketCloseMessage,
  joinMatchLobby,
  LobbyActionError,
  MessageSubmissionError,
  parsePlayerMatchEnvelope,
  parseWebSocketApiErrorEnvelope,
  parseSpectatorMatchEnvelope,
  PublicLeaderboardError,
  PublicMatchHistoryError,
  PublicMatchDetailError,
  PublicMatchesError,
  MatchReplayTickError,
  submitAllianceAction,
  submitGroupChatCreate,
  submitGroupChatMessage,
  submitMatchMessage,
  submitMatchOrders,
  submitTreatyAction,
  startMatchLobby
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
            map: "britain",
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
          map: "britain",
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
        map: "britain",
        tick: 18,
        tick_interval_seconds: 45,
        current_player_count: 3,
        max_player_count: 6,
        open_slot_count: 3,
        roster: [
          { player_id: "player-1", display_name: "Arthur", competitor_kind: "human" },
          { player_id: "player-2", display_name: "Morgana", competitor_kind: "agent" }
        ]
      })
    });

    await expect(
      fetchPublicMatchDetail("match-alpha", fetchImpl as unknown as typeof fetch)
    ).resolves.toEqual({
      match_id: "match-alpha",
      status: "paused",
      map: "britain",
      tick: 18,
      tick_interval_seconds: 45,
      current_player_count: 3,
      max_player_count: 6,
      open_slot_count: 3,
      roster: [
        { player_id: "player-1", display_name: "Arthur", competitor_kind: "human" },
        { player_id: "player-2", display_name: "Morgana", competitor_kind: "agent" }
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
        map: "britain",
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

describe("fetchPublicLeaderboard", () => {
  it("returns the public leaderboard payload from the shipped leaderboard endpoint", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        leaderboard: [
          {
            rank: 1,
            display_name: "Arthur",
            competitor_kind: "human",
            elo: 1210,
            provisional: true,
            matches_played: 1,
            wins: 1,
            losses: 0,
            draws: 0
          }
        ]
      })
    });

    await expect(fetchPublicLeaderboard(fetchImpl as unknown as typeof fetch)).resolves.toEqual({
      leaderboard: [
        {
          rank: 1,
          display_name: "Arthur",
          competitor_kind: "human",
          elo: 1210,
          provisional: true,
          matches_played: 1,
          wins: 1,
          losses: 0,
          draws: 0
        }
      ]
    });

    expect(fetchImpl).toHaveBeenCalledWith("http://127.0.0.1:8000/api/v1/leaderboard", {
      cache: "no-store",
      headers: {
        accept: "application/json"
      }
    });
  });

  it("prefers an explicit browser session API base URL when provided", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ leaderboard: [] })
    });

    await fetchPublicLeaderboard(fetchImpl as unknown as typeof fetch, {
      apiBaseUrl: "https://session.example/"
    });

    expect(fetchImpl).toHaveBeenCalledWith("https://session.example/api/v1/leaderboard", {
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

    await expect(fetchPublicLeaderboard(fetchImpl as unknown as typeof fetch)).rejects.toEqual(
      new PublicLeaderboardError("Unable to load the public leaderboard right now.")
    );
  });

  it("raises a deterministic error when the payload shape is invalid", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        leaderboard: [{ rank: 1, display_name: "Arthur" }]
      })
    });

    await expect(fetchPublicLeaderboard(fetchImpl as unknown as typeof fetch)).rejects.toEqual(
      new PublicLeaderboardError("Unable to load the public leaderboard right now.")
    );
  });
});

describe("fetchPublicMatchHistory", () => {
  it("returns the deterministic persisted tick list from the shipped history endpoint", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        match_id: "match-complete",
        status: "completed",
        current_tick: 155,
        tick_interval_seconds: 30,
        history: [{ tick: 140 }, { tick: 155 }]
      })
    });

    await expect(
      fetchPublicMatchHistory("match-complete", fetchImpl as unknown as typeof fetch)
    ).resolves.toEqual({
      match_id: "match-complete",
      status: "completed",
      current_tick: 155,
      tick_interval_seconds: 30,
      history: [{ tick: 140 }, { tick: 155 }]
    });

    expect(fetchImpl).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/matches/match-complete/history",
      {
        cache: "no-store",
        headers: {
          accept: "application/json"
        }
      }
    );
  });

  it("prefers an explicit browser session API base URL for public history requests", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        match_id: "match-complete",
        status: "completed",
        current_tick: 155,
        tick_interval_seconds: 30,
        history: [{ tick: 140 }, { tick: 155 }]
      })
    });

    await fetchPublicMatchHistory("match-complete", fetchImpl as unknown as typeof fetch, {
      apiBaseUrl: "https://session.example/"
    });

    expect(fetchImpl).toHaveBeenCalledWith(
      "https://session.example/api/v1/matches/match-complete/history",
      {
        cache: "no-store",
        headers: {
          accept: "application/json"
        }
      }
    );
  });

  it("raises a deterministic not-found error when the public history route returns match_not_found", async () => {
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
      fetchPublicMatchHistory("missing", fetchImpl as unknown as typeof fetch)
    ).rejects.toEqual(
      new PublicMatchHistoryError(
        "This completed match history is unavailable. It may not exist.",
        "not_found"
      )
    );
  });

  it("raises a deterministic unavailable error when the DB-backed history route is unavailable", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({
        error: {
          code: "match_history_unavailable",
          message: "Persisted match history is only available in DB-backed mode."
        }
      })
    });

    await expect(
      fetchPublicMatchHistory("match-complete", fetchImpl as unknown as typeof fetch)
    ).rejects.toEqual(
      new PublicMatchHistoryError("Unable to load match history right now.", "unavailable")
    );
  });

  it("raises a deterministic unavailable error when the history payload shape is invalid", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        match_id: "match-complete",
        history: [{ tick: "broken" }]
      })
    });

    await expect(
      fetchPublicMatchHistory("match-complete", fetchImpl as unknown as typeof fetch)
    ).rejects.toEqual(
      new PublicMatchHistoryError("Unable to load match history right now.", "unavailable")
    );
  });
});

describe("fetchMatchReplayTick", () => {
  it("returns the shipped persisted replay snapshot from the tick route", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        match_id: "match-complete",
        tick: 155,
        state_snapshot: {
          cities: {
            london: {
              owner: "Arthur",
              population: 12
            }
          }
        },
        orders: {
          movements: [{ army_id: "army-1", destination: "york" }]
        },
        events: {
          summary: ["Convoy secured"]
        }
      })
    });

    await expect(
      fetchMatchReplayTick("match-complete", 155, fetchImpl as unknown as typeof fetch)
    ).resolves.toEqual({
      match_id: "match-complete",
      tick: 155,
      state_snapshot: {
        cities: {
          london: {
            owner: "Arthur",
            population: 12
          }
        }
      },
      orders: {
        movements: [{ army_id: "army-1", destination: "york" }]
      },
      events: {
        summary: ["Convoy secured"]
      }
    });

    expect(fetchImpl).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/matches/match-complete/history/155",
      {
        cache: "no-store",
        headers: {
          accept: "application/json"
        }
      }
    );
  });

  it("prefers an explicit browser session API base URL for replay tick requests", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        match_id: "match-complete",
        tick: 155,
        state_snapshot: { cities: {} },
        orders: {},
        events: []
      })
    });

    await fetchMatchReplayTick("match-complete", 155, fetchImpl as unknown as typeof fetch, {
      apiBaseUrl: "https://session.example/"
    });

    expect(fetchImpl).toHaveBeenCalledWith(
      "https://session.example/api/v1/matches/match-complete/history/155",
      {
        cache: "no-store",
        headers: {
          accept: "application/json"
        }
      }
    );
  });

  it("raises a deterministic tick-not-found error when the replay tick route returns tick_not_found", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({
        error: {
          code: "tick_not_found",
          message: "Tick 999 was not found for match 'match-complete'."
        }
      })
    });

    await expect(
      fetchMatchReplayTick("match-complete", 999, fetchImpl as unknown as typeof fetch)
    ).rejects.toEqual(
      new MatchReplayTickError(
        "This replay tick is unavailable for the selected match.",
        "tick_not_found"
      )
    );
  });

  it("raises a deterministic match-not-found error when the replay tick route returns match_not_found", async () => {
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
      fetchMatchReplayTick("missing", 155, fetchImpl as unknown as typeof fetch)
    ).rejects.toEqual(
      new MatchReplayTickError(
        "This completed match history is unavailable. It may not exist.",
        "match_not_found"
      )
    );
  });

  it("raises a deterministic unavailable error when the replay payload shape is invalid", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        match_id: "match-complete",
        tick: 155,
        state_snapshot: [],
        orders: {},
        events: {}
      })
    });

    await expect(
      fetchMatchReplayTick("match-complete", 155, fetchImpl as unknown as typeof fetch)
    ).rejects.toEqual(
      new MatchReplayTickError("Unable to load this replay tick right now.", "unavailable")
    );
  });
});

describe("fetchCompletedMatches", () => {
  it("returns the compact completed-match browse payload from the shipped endpoint", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        matches: [
          {
            match_id: "match-complete",
            map: "britain",
            final_tick: 155,
            tick_interval_seconds: 30,
            player_count: 3,
            completed_at: "2026-03-29T08:30:00Z",
            winning_alliance_name: "Iron Crown",
            winning_player_display_names: ["Arthur", "Morgana"]
          }
        ]
      })
    });

    await expect(fetchCompletedMatches(fetchImpl as unknown as typeof fetch)).resolves.toEqual({
      matches: [
        {
          match_id: "match-complete",
          map: "britain",
          final_tick: 155,
          tick_interval_seconds: 30,
          player_count: 3,
          completed_at: "2026-03-29T08:30:00Z",
          winning_alliance_name: "Iron Crown",
          winning_player_display_names: ["Arthur", "Morgana"]
        }
      ]
    });

    expect(fetchImpl).toHaveBeenCalledWith("http://127.0.0.1:8000/api/v1/matches/completed", {
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

    await fetchCompletedMatches(fetchImpl as unknown as typeof fetch, {
      apiBaseUrl: "https://session.example/"
    });

    expect(fetchImpl).toHaveBeenCalledWith("https://session.example/api/v1/matches/completed", {
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

    await expect(fetchCompletedMatches(fetchImpl as unknown as typeof fetch)).rejects.toEqual(
      new CompletedMatchesError("Unable to load completed matches right now.")
    );
  });

  it("raises a deterministic error when the payload shape is invalid", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        matches: [{ match_id: "broken" }]
      })
    });

    await expect(fetchCompletedMatches(fetchImpl as unknown as typeof fetch)).rejects.toEqual(
      new CompletedMatchesError("Unable to load completed matches right now.")
    );
  });
});

describe("submitMatchOrders", () => {
  it("posts the shipped order-only command envelope with bearer auth and returns typed accepted metadata", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      status: 202,
      json: async () => ({
        status: "accepted",
        match_id: "match-alpha",
        player_id: "player-2",
        tick: 143,
        orders: {
          status: "accepted",
          match_id: "match-alpha",
          player_id: "player-2",
          tick: 143,
          submission_index: 2
        },
        messages: [],
        treaties: [],
        alliance: null
      })
    });

    await expect(
      submitMatchOrders(
        {
          match_id: "match-alpha",
          tick: 143,
          orders: {
            movements: [{ army_id: "army-7", destination: "york" }],
            recruitment: [{ city: "manchester", troops: 5 }],
            upgrades: [{ city: "london", track: "military", target_tier: 2 }],
            transfers: [{ to: "player-3", resource: "money", amount: 25 }]
          }
        },
        "human-token",
        fetchImpl as unknown as typeof fetch
      )
    ).resolves.toEqual({
      status: "accepted",
      match_id: "match-alpha",
      player_id: "player-2",
      tick: 143,
      submission_index: 2
    });

    expect(fetchImpl).toHaveBeenCalledWith("http://127.0.0.1:8000/api/v1/matches/match-alpha/commands", {
      method: "POST",
      cache: "no-store",
      headers: {
        accept: "application/json",
        authorization: "Bearer human-token",
        "content-type": "application/json"
      },
      body: JSON.stringify({
        match_id: "match-alpha",
        tick: 143,
        orders: {
          movements: [{ army_id: "army-7", destination: "york" }],
          recruitment: [{ city: "manchester", troops: 5 }],
          upgrades: [{ city: "london", track: "military", target_tier: 2 }],
          transfers: [{ to: "player-3", resource: "money", amount: 25 }]
        },
        messages: [],
        treaties: [],
        alliance: null
      })
    });
  });

  it("prefers an explicit browser session API base URL for command submissions", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      status: 202,
      json: async () => ({
        status: "accepted",
        match_id: "match-alpha",
        player_id: "player-2",
        tick: 143,
        orders: {
          status: "accepted",
          match_id: "match-alpha",
          player_id: "player-2",
          tick: 143,
          submission_index: 3
        },
        messages: [],
        treaties: [],
        alliance: null
      })
    });

    await submitMatchOrders(
      {
        match_id: "match-alpha",
        tick: 143,
        orders: {
          movements: [],
          recruitment: [],
          upgrades: [],
          transfers: []
        }
      },
      "human-token",
      fetchImpl as unknown as typeof fetch,
      { apiBaseUrl: "https://session.example/" }
    );

    expect(fetchImpl).toHaveBeenCalledWith("https://session.example/api/v1/matches/match-alpha/commands", {
      method: "POST",
      cache: "no-store",
      headers: {
        accept: "application/json",
        authorization: "Bearer human-token",
        "content-type": "application/json"
      },
      body: JSON.stringify({
        match_id: "match-alpha",
        tick: 143,
        orders: {
          movements: [],
          recruitment: [],
          upgrades: [],
          transfers: []
        },
        messages: [],
        treaties: [],
        alliance: null
      })
    });
  });

  it("turns structured api error envelopes into a deterministic client error", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({
        error: {
          code: "tick_mismatch",
          message: "Command payload tick '141' does not match current match tick '142'."
        }
      })
    });

    await expect(
      submitMatchOrders(
        {
          match_id: "match-alpha",
          tick: 141,
          orders: {
            movements: [],
            recruitment: [],
            upgrades: [],
            transfers: []
          }
        },
        "human-token",
        fetchImpl as unknown as typeof fetch
      )
    ).rejects.toEqual(
      new CommandSubmissionError(
        "Command payload tick '141' does not match current match tick '142'.",
        "tick_mismatch",
        400
      )
    );
  });

  it("normalizes transport rejections into a deterministic client error", async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new TypeError("fetch failed"));

    await expect(
      submitMatchOrders(
        {
          match_id: "match-alpha",
          tick: 143,
          orders: {
            movements: [],
            recruitment: [],
            upgrades: [],
            transfers: []
          }
        },
        "human-token",
        fetchImpl as unknown as typeof fetch
      )
    ).rejects.toEqual(
      new CommandSubmissionError("Unable to submit orders right now.", "command_submission_unavailable", 500)
    );
  });

  it("raises a deterministic client error when the accepted response is malformed", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      status: 202,
      json: async () => ({
        status: "accepted",
        match_id: "match-alpha",
        player_id: "player-2",
        tick: 143,
        orders: null,
        messages: [],
        treaties: [],
        alliance: null
      })
    });

    await expect(
      submitMatchOrders(
        {
          match_id: "match-alpha",
          tick: 143,
          orders: {
            movements: [],
            recruitment: [],
            upgrades: [],
            transfers: []
          }
        },
        "human-token",
        fetchImpl as unknown as typeof fetch
      )
    ).rejects.toEqual(
      new CommandSubmissionError(
        "Unable to submit orders right now.",
        "invalid_command_response",
        202
      )
    );
  });
});

describe("submitGroupChatCreate", () => {
  it("posts the shipped group-chat creation payload with bearer auth and returns typed accepted metadata", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      status: 202,
      json: async () => ({
        status: "accepted",
        match_id: "match-alpha",
        group_chat: {
          group_chat_id: "council-gold",
          name: "Gold Council",
          member_ids: ["player-2", "player-3"],
          created_by: "player-2",
          created_tick: 144
        }
      })
    });

    await expect(
      submitGroupChatCreate(
        {
          match_id: "match-alpha",
          tick: 144,
          name: "Gold Council",
          member_ids: ["player-3"]
        },
        "human-token",
        fetchImpl as unknown as typeof fetch
      )
    ).resolves.toEqual({
      status: "accepted",
      match_id: "match-alpha",
      group_chat: {
        group_chat_id: "council-gold",
        name: "Gold Council",
        member_ids: ["player-2", "player-3"],
        created_by: "player-2",
        created_tick: 144
      }
    });

    expect(fetchImpl).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/matches/match-alpha/group-chats",
      {
        method: "POST",
        cache: "no-store",
        headers: {
          accept: "application/json",
          authorization: "Bearer human-token",
          "content-type": "application/json"
        },
        body: JSON.stringify({
          match_id: "match-alpha",
          tick: 144,
          name: "Gold Council",
          member_ids: ["player-3"]
        })
      }
    );
  });

  it("surfaces structured API errors as deterministic group-chat creation errors", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({
        error: {
          code: "tick_mismatch",
          message: "Group chat payload tick '143' does not match current match tick '144'."
        }
      })
    });

    await expect(
      submitGroupChatCreate(
        {
          match_id: "match-alpha",
          tick: 143,
          name: "Gold Council",
          member_ids: ["player-3"]
        },
        "human-token",
        fetchImpl as unknown as typeof fetch
      )
    ).rejects.toEqual(
      new GroupChatCreateError(
        "Group chat payload tick '143' does not match current match tick '144'.",
        "tick_mismatch",
        400
      )
    );
  });

  it("fails closed when the accepted response shape is invalid", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      status: 202,
      json: async () => ({
        status: "accepted",
        match_id: "match-alpha",
        group_chat: {
          name: "Gold Council"
        }
      })
    });

    await expect(
      submitGroupChatCreate(
        {
          match_id: "match-alpha",
          tick: 144,
          name: "Gold Council",
          member_ids: ["player-3"]
        },
        "human-token",
        fetchImpl as unknown as typeof fetch
      )
    ).rejects.toEqual(
      new GroupChatCreateError(
        "Unable to create group chat right now.",
        "invalid_group_chat_create_response",
        202
      )
    );
  });

  it("uses an explicit apiBaseUrl override for group-chat creation submissions", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      status: 202,
      json: async () => ({
        status: "accepted",
        match_id: "match-alpha",
        group_chat: {
          group_chat_id: "council-gold",
          name: "Gold Council",
          member_ids: ["player-2", "player-3"],
          created_by: "player-2",
          created_tick: 144
        }
      })
    });

    await submitGroupChatCreate(
      {
        match_id: "match-alpha",
        tick: 144,
        name: "Gold Council",
        member_ids: ["player-3"]
      },
      "human-token",
      fetchImpl as unknown as typeof fetch,
      { apiBaseUrl: "https://session.example/game-api/" }
    );

    expect(fetchImpl).toHaveBeenCalledWith(
      "https://session.example/game-api/api/v1/matches/match-alpha/group-chats",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          authorization: "Bearer human-token"
        })
      })
    );
  });

  it("uses group-chat-specific fallback copy when the request cannot reach the backend", async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new Error("network down"));

    await expect(
      submitGroupChatCreate(
        {
          match_id: "match-alpha",
          tick: 144,
          name: "Gold Council",
          member_ids: ["player-3"]
        },
        "human-token",
        fetchImpl as unknown as typeof fetch
      )
    ).rejects.toEqual(
      new GroupChatCreateError(
        "Unable to create group chat right now.",
        "group_chat_create_unavailable",
        500
      )
    );
  });
});

describe("message submission helpers", () => {
  it("posts the shipped world message request shape with bearer auth and returns typed accepted metadata", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      status: 202,
      json: async () => ({
        status: "accepted",
        match_id: "match-alpha",
        message_id: 16,
        channel: "world",
        sender_id: "player-2",
        recipient_id: null,
        tick: 143,
        content: "Stand ready."
      })
    });

    await expect(
      submitMatchMessage(
        {
          match_id: "match-alpha",
          tick: 143,
          channel: "world",
          recipient_id: null,
          content: "Stand ready."
        },
        "human-token",
        fetchImpl as unknown as typeof fetch
      )
    ).resolves.toEqual({
      status: "accepted",
      match_id: "match-alpha",
      message_id: 16,
      channel: "world",
      sender_id: "player-2",
      recipient_id: null,
      tick: 143,
      content: "Stand ready."
    });

    expect(fetchImpl).toHaveBeenCalledWith("http://127.0.0.1:8000/api/v1/matches/match-alpha/messages", {
      method: "POST",
      cache: "no-store",
      headers: {
        accept: "application/json",
        authorization: "Bearer human-token",
        "content-type": "application/json"
      },
      body: JSON.stringify({
        match_id: "match-alpha",
        tick: 143,
        channel: "world",
        recipient_id: null,
        content: "Stand ready."
      })
    });
  });

  it("posts the shipped world/direct message request shape with bearer auth and returns typed accepted metadata", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      status: 202,
      json: async () => ({
        status: "accepted",
        match_id: "match-alpha",
        message_id: 17,
        channel: "direct",
        sender_id: "player-2",
        recipient_id: "player-3",
        tick: 143,
        content: "Hold the western road."
      })
    });

    await expect(
      submitMatchMessage(
        {
          match_id: "match-alpha",
          tick: 143,
          channel: "direct",
          recipient_id: "player-3",
          content: "Hold the western road."
        },
        "human-token",
        fetchImpl as unknown as typeof fetch
      )
    ).resolves.toEqual({
      status: "accepted",
      match_id: "match-alpha",
      message_id: 17,
      channel: "direct",
      sender_id: "player-2",
      recipient_id: "player-3",
      tick: 143,
      content: "Hold the western road."
    });

    expect(fetchImpl).toHaveBeenCalledWith("http://127.0.0.1:8000/api/v1/matches/match-alpha/messages", {
      method: "POST",
      cache: "no-store",
      headers: {
        accept: "application/json",
        authorization: "Bearer human-token",
        "content-type": "application/json"
      },
      body: JSON.stringify({
        match_id: "match-alpha",
        tick: 143,
        channel: "direct",
        recipient_id: "player-3",
        content: "Hold the western road."
      })
    });
  });

  it("posts the shipped group-chat message request shape with bearer auth and returns typed accepted metadata", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      status: 202,
      json: async () => ({
        status: "accepted",
        match_id: "match-alpha",
        group_chat_id: "council-red",
        message: {
          message_id: 29,
          group_chat_id: "council-red",
          sender_id: "player-2",
          tick: 144,
          content: "Reinforce York at dawn."
        }
      })
    });

    await expect(
      submitGroupChatMessage(
        "council-red",
        {
          match_id: "match-alpha",
          tick: 144,
          content: "Reinforce York at dawn."
        },
        "human-token",
        fetchImpl as unknown as typeof fetch
      )
    ).resolves.toEqual({
      status: "accepted",
      match_id: "match-alpha",
      group_chat_id: "council-red",
      message: {
        message_id: 29,
        group_chat_id: "council-red",
        sender_id: "player-2",
        tick: 144,
        content: "Reinforce York at dawn."
      }
    });

    expect(fetchImpl).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/matches/match-alpha/group-chats/council-red/messages",
      {
        method: "POST",
        cache: "no-store",
        headers: {
          accept: "application/json",
          authorization: "Bearer human-token",
          "content-type": "application/json"
        },
        body: JSON.stringify({
          match_id: "match-alpha",
          tick: 144,
          content: "Reinforce York at dawn."
        })
      }
    );
  });

  it("turns structured message api error envelopes into a deterministic client error with code and status", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({
        error: {
          code: "tick_mismatch",
          message: "Message payload tick '142' does not match current match tick '143'."
        }
      })
    });

    await expect(
      submitMatchMessage(
        {
          match_id: "match-alpha",
          tick: 142,
          channel: "world",
          recipient_id: null,
          content: "Stand ready."
        },
        "human-token",
        fetchImpl as unknown as typeof fetch
      )
    ).rejects.toEqual(
      new MessageSubmissionError(
        "Message payload tick '142' does not match current match tick '143'.",
        "tick_mismatch",
        400
      )
    );
  });

  it("raises a deterministic client error when an accepted world/direct response is malformed", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      status: 202,
      json: async () => ({
        status: "accepted",
        match_id: "match-alpha",
        message_id: 17,
        channel: "world",
        sender_id: "player-2",
        recipient_id: null,
        tick: 143
      })
    });

    await expect(
      submitMatchMessage(
        {
          match_id: "match-alpha",
          tick: 143,
          channel: "world",
          recipient_id: null,
          content: "Stand ready."
        },
        "human-token",
        fetchImpl as unknown as typeof fetch
      )
    ).rejects.toEqual(
      new MessageSubmissionError(
        "Unable to submit message right now.",
        "invalid_message_response",
        202
      )
    );
  });
});

describe("diplomacy submission helpers", () => {
  it("posts the shipped treaty action request shape with bearer auth and returns typed accepted metadata", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      status: 202,
      json: async () => ({
        status: "accepted",
        match_id: "match-alpha",
        treaty: {
          treaty_id: 8,
          player_a_id: "player-2",
          player_b_id: "player-3",
          treaty_type: "non_aggression",
          status: "proposed",
          proposed_by: "player-2",
          proposed_tick: 144,
          signed_tick: null,
          withdrawn_by: null,
          withdrawn_tick: null
        }
      })
    });

    await expect(
      submitTreatyAction(
        {
          match_id: "match-alpha",
          counterparty_id: "player-3",
          action: "propose",
          treaty_type: "non_aggression"
        },
        "human-token",
        fetchImpl as unknown as typeof fetch
      )
    ).resolves.toEqual({
      status: "accepted",
      match_id: "match-alpha",
      treaty: {
        treaty_id: 8,
        player_a_id: "player-2",
        player_b_id: "player-3",
        treaty_type: "non_aggression",
        status: "proposed",
        proposed_by: "player-2",
        proposed_tick: 144,
        signed_tick: null,
        withdrawn_by: null,
        withdrawn_tick: null
      }
    });

    expect(fetchImpl).toHaveBeenCalledWith("http://127.0.0.1:8000/api/v1/matches/match-alpha/treaties", {
      method: "POST",
      cache: "no-store",
      headers: {
        accept: "application/json",
        authorization: "Bearer human-token",
        "content-type": "application/json"
      },
      body: JSON.stringify({
        match_id: "match-alpha",
        counterparty_id: "player-3",
        action: "propose",
        treaty_type: "non_aggression"
      })
    });
  });

  it("posts the shipped alliance create, join, and leave request shapes with bearer auth", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 202,
        json: async () => ({
          status: "accepted",
          match_id: "match-alpha",
          player_id: "player-2",
          alliance: {
            alliance_id: "alliance-blue",
            name: "Blue League",
            leader_id: "player-2",
            formed_tick: 144,
            members: [{ player_id: "player-2", joined_tick: 144 }]
          }
        })
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 202,
        json: async () => ({
          status: "accepted",
          match_id: "match-alpha",
          player_id: "player-2",
          alliance: {
            alliance_id: "alliance-red",
            name: "Red Council",
            leader_id: "player-1",
            formed_tick: 140,
            members: [
              { player_id: "player-1", joined_tick: 140 },
              { player_id: "player-2", joined_tick: 144 }
            ]
          }
        })
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 202,
        json: async () => ({
          status: "accepted",
          match_id: "match-alpha",
          player_id: "player-2",
          alliance: {
            alliance_id: "alliance-red",
            name: "Red Council",
            leader_id: "player-1",
            formed_tick: 140,
            members: [{ player_id: "player-1", joined_tick: 140 }]
          }
        })
      });

    await expect(
      submitAllianceAction(
        {
          match_id: "match-alpha",
          action: "create",
          name: "Blue League"
        },
        "human-token",
        fetchImpl as unknown as typeof fetch
      )
    ).resolves.toEqual({
      status: "accepted",
      match_id: "match-alpha",
      player_id: "player-2",
      alliance: {
        alliance_id: "alliance-blue",
        name: "Blue League",
        leader_id: "player-2",
        formed_tick: 144,
        members: [{ player_id: "player-2", joined_tick: 144 }]
      }
    });

    await expect(
      submitAllianceAction(
        {
          match_id: "match-alpha",
          action: "join",
          alliance_id: "alliance-red"
        },
        "human-token",
        fetchImpl as unknown as typeof fetch
      )
    ).resolves.toEqual({
      status: "accepted",
      match_id: "match-alpha",
      player_id: "player-2",
      alliance: {
        alliance_id: "alliance-red",
        name: "Red Council",
        leader_id: "player-1",
        formed_tick: 140,
        members: [
          { player_id: "player-1", joined_tick: 140 },
          { player_id: "player-2", joined_tick: 144 }
        ]
      }
    });

    await expect(
      submitAllianceAction(
        {
          match_id: "match-alpha",
          action: "leave"
        },
        "human-token",
        fetchImpl as unknown as typeof fetch
      )
    ).resolves.toEqual({
      status: "accepted",
      match_id: "match-alpha",
      player_id: "player-2",
      alliance: {
        alliance_id: "alliance-red",
        name: "Red Council",
        leader_id: "player-1",
        formed_tick: 140,
        members: [{ player_id: "player-1", joined_tick: 140 }]
      }
    });

    expect(fetchImpl).toHaveBeenNthCalledWith(1, "http://127.0.0.1:8000/api/v1/matches/match-alpha/alliances", {
      method: "POST",
      cache: "no-store",
      headers: {
        accept: "application/json",
        authorization: "Bearer human-token",
        "content-type": "application/json"
      },
      body: JSON.stringify({
        match_id: "match-alpha",
        action: "create",
        name: "Blue League"
      })
    });

    expect(fetchImpl).toHaveBeenNthCalledWith(2, "http://127.0.0.1:8000/api/v1/matches/match-alpha/alliances", {
      method: "POST",
      cache: "no-store",
      headers: {
        accept: "application/json",
        authorization: "Bearer human-token",
        "content-type": "application/json"
      },
      body: JSON.stringify({
        match_id: "match-alpha",
        action: "join",
        alliance_id: "alliance-red"
      })
    });

    expect(fetchImpl).toHaveBeenNthCalledWith(3, "http://127.0.0.1:8000/api/v1/matches/match-alpha/alliances", {
      method: "POST",
      cache: "no-store",
      headers: {
        accept: "application/json",
        authorization: "Bearer human-token",
        "content-type": "application/json"
      },
      body: JSON.stringify({
        match_id: "match-alpha",
        action: "leave"
      })
    });
  });

  it("turns structured diplomacy api error envelopes into deterministic treaty and alliance client errors", async () => {
    const treatyFetchImpl = vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({
        error: {
          code: "treaty_conflict",
          message: "A non_aggression treaty with player-3 is already active."
        }
      })
    });
    const allianceFetchImpl = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      json: async () => ({
        error: {
          code: "alliance_leave_forbidden",
          message: "Alliance leaders cannot leave without disbanding first."
        }
      })
    });

    await expect(
      submitTreatyAction(
        {
          match_id: "match-alpha",
          counterparty_id: "player-3",
          action: "propose",
          treaty_type: "non_aggression"
        },
        "human-token",
        treatyFetchImpl as unknown as typeof fetch
      )
    ).rejects.toEqual(
      new DiplomacySubmissionError(
        "A non_aggression treaty with player-3 is already active.",
        "treaty_conflict",
        409
      )
    );

    await expect(
      submitAllianceAction(
        {
          match_id: "match-alpha",
          action: "leave"
        },
        "human-token",
        allianceFetchImpl as unknown as typeof fetch
      )
    ).rejects.toEqual(
      new DiplomacySubmissionError(
        "Alliance leaders cannot leave without disbanding first.",
        "alliance_leave_forbidden",
        403
      )
    );
  });

  it("normalizes diplomacy transport rejections into a deterministic client error", async () => {
    const treatyFetchImpl = vi.fn().mockRejectedValue(new TypeError("fetch failed"));
    const allianceFetchImpl = vi.fn().mockRejectedValue(new TypeError("fetch failed"));

    await expect(
      submitTreatyAction(
        {
          match_id: "match-alpha",
          counterparty_id: "player-3",
          action: "propose",
          treaty_type: "trade"
        },
        "human-token",
        treatyFetchImpl as unknown as typeof fetch
      )
    ).rejects.toEqual(
      new DiplomacySubmissionError(
        "Unable to submit diplomacy action right now.",
        "diplomacy_submission_unavailable",
        500
      )
    );

    await expect(
      submitAllianceAction(
        {
          match_id: "match-alpha",
          action: "create",
          name: "Blue League"
        },
        "human-token",
        allianceFetchImpl as unknown as typeof fetch
      )
    ).rejects.toEqual(
      new DiplomacySubmissionError(
        "Unable to submit diplomacy action right now.",
        "diplomacy_submission_unavailable",
        500
      )
    );
  });

  it("rejects malformed diplomacy success responses with a deterministic client error", async () => {
    const treatyFetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      status: 202,
      json: async () => ({ status: "accepted", match_id: "match-alpha", treaty: null })
    });
    const allianceFetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      status: 202,
      json: async () => ({ status: "accepted", match_id: "match-alpha", player_id: "player-2", alliance: null })
    });

    await expect(
      submitTreatyAction(
        {
          match_id: "match-alpha",
          counterparty_id: "player-3",
          action: "accept",
          treaty_type: "trade"
        },
        "human-token",
        treatyFetchImpl as unknown as typeof fetch
      )
    ).rejects.toEqual(
      new DiplomacySubmissionError(
        "Unable to submit diplomacy action right now.",
        "invalid_diplomacy_response",
        202
      )
    );

    await expect(
      submitAllianceAction(
        {
          match_id: "match-alpha",
          action: "leave"
        },
        "human-token",
        allianceFetchImpl as unknown as typeof fetch
      )
    ).rejects.toEqual(
      new DiplomacySubmissionError(
        "Unable to submit diplomacy action right now.",
        "invalid_diplomacy_response",
        202
      )
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

describe("player realtime helpers", () => {
  it("parses a valid player tick update envelope", () => {
    expect(
      parsePlayerMatchEnvelope({
        type: "tick_update",
        data: {
          match_id: "match-alpha",
          viewer_role: "player",
          player_id: "player-2",
          state: {
            match_id: "match-alpha",
            tick: 143,
            player_id: "player-2",
            resources: {
              food: 120,
              production: 85,
              money: 200
            },
            cities: {
              manchester: {
                owner: "player-2",
                visibility: "full",
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
                visibility: "partial",
                population: "unknown",
                resources: "unknown",
                upgrades: "unknown",
                garrison: "unknown",
                building_queue: "unknown"
              }
            },
            visible_armies: [
              {
                id: "army-1",
                owner: "player-2",
                visibility: "full",
                troops: 5,
                location: "manchester",
                destination: null,
                path: null,
                ticks_remaining: 0
              },
              {
                id: "army-2",
                owner: "player-3",
                visibility: "partial",
                troops: "unknown",
                location: null,
                destination: "birmingham",
                path: "unknown",
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
              message_id: 2,
              channel: "world",
              sender_id: "player-1",
              recipient_id: null,
              tick: 143,
              content: "War drums."
            }
          ],
          direct_messages: [
            {
              message_id: 3,
              channel: "direct",
              sender_id: "player-1",
              recipient_id: "player-2",
              tick: 143,
              content: "Hold the line."
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
              message_id: 4,
              group_chat_id: "council-red",
              sender_id: "player-2",
              tick: 143,
              content: "Ready."
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
      })
    ).toMatchObject({
      type: "tick_update",
      data: {
        viewer_role: "player",
        player_id: "player-2",
        state: {
          player_id: "player-2",
          cities: {
            birmingham: {
              visibility: "partial",
              garrison: "unknown"
            }
          },
          visible_armies: [
            { id: "army-1", visibility: "full", troops: 5 },
            { id: "army-2", visibility: "partial", troops: "unknown", path: "unknown" }
          ],
          alliance_members: ["player-1", "player-2"]
        },
        direct_messages: [{ content: "Hold the line." }],
        group_chats: [{ name: "Red Council" }],
        treaties: [{ status: "accepted" }],
        alliances: [{ alliance_id: "alliance-red" }]
      }
    });
  });

  it("rejects malformed player realtime payloads deterministically", () => {
    expect(() =>
      parsePlayerMatchEnvelope({
        type: "tick_update",
        data: {
          match_id: "match-alpha",
          viewer_role: "player",
          player_id: "player-2",
          state: {
            tick: "143"
          }
        }
      })
    ).toThrowError("Unable to parse player live match update.");
  });

  it("parses a structured websocket api error envelope for auth failures", () => {
    expect(
      parseWebSocketApiErrorEnvelope({
        error: {
          code: "invalid_websocket_auth",
          message: "Player websocket connections require a valid human JWT token query parameter."
        }
      })
    ).toEqual({
      error: {
        code: "invalid_websocket_auth",
        message: "Player websocket connections require a valid human JWT token query parameter."
      }
    });
  });

  it("maps known player websocket close reasons to deterministic user messages", () => {
    expect(getPlayerWebSocketCloseMessage("human_not_joined")).toBe(
      "Join this match as a human player before opening the authenticated live page."
    );
    expect(getPlayerWebSocketCloseMessage("match_not_found")).toBe(
      "This match is unavailable. It may not exist or may already be completed."
    );
    expect(getPlayerWebSocketCloseMessage("invalid_websocket_auth")).toBe(
      "This live player page requires a valid human bearer token before it can connect."
    );
    expect(getPlayerWebSocketCloseMessage("player_auth_mismatch")).toBe(
      "This bearer token does not belong to the requested player."
    );
    expect(getPlayerWebSocketCloseMessage("unknown_reason")).toBeNull();
  });

  it("builds the shipped player websocket URL from the configured API base URL and token", () => {
    expect(
      buildPlayerMatchWebSocketUrl("match alpha", "human jwt", {
        apiBaseUrl: "https://session.example/"
      })
    ).toBe("wss://session.example/ws/match/match%20alpha?viewer=player&token=human+jwt");
  });

  it("preserves a configured base-path prefix when building the player websocket URL", () => {
    expect(
      buildPlayerMatchWebSocketUrl("match-alpha", "human-jwt", {
        apiBaseUrl: "https://session.example/game-api"
      })
    ).toBe("wss://session.example/game-api/ws/match/match-alpha?viewer=player&token=human-jwt");
  });
});


describe("human lobby lifecycle helpers", () => {
  it("sends bearer auth to the existing create route and parses the compact response", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({
        match_id: "match-alpha",
        status: "lobby",
        map: "britain",
        tick: 0,
        tick_interval_seconds: 20,
        current_player_count: 1,
        max_player_count: 4,
        open_slot_count: 3,
        creator_player_id: "player-1"
      })
    });

    await expect(createMatchLobby({
      map: "britain", tick_interval_seconds: 20, max_players: 4, victory_city_threshold: 13, starting_cities_per_player: 2
    }, "human-jwt", fetchImpl as unknown as typeof fetch, { apiBaseUrl: "https://session.example/" })).resolves.toMatchObject({
      match_id: "match-alpha",
      creator_player_id: "player-1"
    });

    expect(fetchImpl).toHaveBeenCalledWith("https://session.example/api/v1/matches", expect.objectContaining({
      method: "POST",
      headers: expect.objectContaining({ authorization: "Bearer human-jwt", accept: "application/json", "content-type": "application/json" })
    }));
  });

  it("surfaces structured join and start errors deterministically", async () => {
    const joinFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ error: { code: "match_not_joinable", message: "Match 'match-alpha' is full." } })
    });
    const startFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      json: async () => ({ error: { code: "match_start_forbidden", message: "Authenticated human does not own lobby 'match-alpha'." } })
    });

    await expect(joinMatchLobby({ match_id: "match-alpha" }, "human-jwt", joinFetch as unknown as typeof fetch)).rejects.toEqual(
      new LobbyActionError("Match 'match-alpha' is full.", "match_not_joinable", 409)
    );
    await expect(startMatchLobby("match-alpha", "human-jwt", startFetch as unknown as typeof fetch)).rejects.toEqual(
      new LobbyActionError("Authenticated human does not own lobby 'match-alpha'.", "match_start_forbidden", 403)
    );
  });

  it("fails closed on malformed lobby success payloads", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ status: "accepted" }) });

    await expect(joinMatchLobby({ match_id: "match-alpha" }, "human-jwt", fetchImpl as unknown as typeof fetch)).rejects.toEqual(
      new LobbyActionError("Unable to complete the requested lobby action right now.", "invalid_lobby_response", 200)
    );
  });
});
