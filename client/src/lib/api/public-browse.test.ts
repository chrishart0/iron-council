import { describe, expect, it, vi } from "vitest";
import {
  CompletedMatchesError,
  fetchCompletedMatches,
  fetchPublicMatchDetail,
  fetchPublicMatches,
  PublicMatchDetailError,
  PublicMatchesError
} from "./public-browse";

describe("public fetch helper failure normalization", () => {
  const transportCases = [
    {
      name: "fetchPublicMatches",
      invoke: (fetchImpl: typeof fetch) => fetchPublicMatches(fetchImpl),
      expected: new PublicMatchesError("Unable to load public matches right now.")
    },
    {
      name: "fetchPublicMatchDetail",
      invoke: (fetchImpl: typeof fetch) => fetchPublicMatchDetail("match-alpha", fetchImpl),
      expected: new PublicMatchDetailError("Unable to load this public match right now.", "unavailable")
    },
    {
      name: "fetchCompletedMatches",
      invoke: (fetchImpl: typeof fetch) => fetchCompletedMatches(fetchImpl),
      expected: new CompletedMatchesError("Unable to load completed matches right now.")
    }
  ] satisfies Array<{
    name: string;
    invoke: (fetchImpl: typeof fetch) => Promise<unknown>;
    expected: Error;
  }>;

  it.each(transportCases)(
    "maps transport failures for $name to the deterministic exported public error",
    async ({ invoke, expected }) => {
      const fetchImpl = vi.fn<typeof fetch>().mockRejectedValue(new TypeError("fetch failed"));

      await expect(invoke(fetchImpl)).rejects.toEqual(expected);
    }
  );

  it.each(transportCases)(
    "maps malformed successful json for $name to the deterministic exported public error",
    async ({ invoke, expected }) => {
      const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => {
          throw new SyntaxError("Unexpected token < in JSON");
        }
      } as unknown as Response);

      await expect(invoke(fetchImpl)).rejects.toEqual(expected);
    }
  );
});

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
          {
            player_id: "player-1",
            display_name: "Arthur",
            competitor_kind: "human",
            agent_id: null,
            human_id: "human:arthur"
          },
          {
            player_id: "player-2",
            display_name: "Morgana",
            competitor_kind: "agent",
            agent_id: "agent-player-2",
            human_id: null
          }
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
        {
          player_id: "player-1",
          display_name: "Arthur",
          competitor_kind: "human",
          agent_id: null,
          human_id: "human:arthur"
        },
        {
          player_id: "player-2",
          display_name: "Morgana",
          competitor_kind: "agent",
          agent_id: "agent-player-2",
          human_id: null
        }
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

  it("accepts legacy public match-detail roster rows that omit additive identity fields", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        match_id: "legacy-contract",
        status: "active",
        map: "britain",
        tick: 18,
        tick_interval_seconds: 45,
        current_player_count: 2,
        max_player_count: 6,
        open_slot_count: 4,
        roster: [
          {
            player_id: "player-1",
            display_name: "Arthur",
            competitor_kind: "human"
          },
          {
            player_id: "player-2",
            display_name: "Morgana",
            competitor_kind: "agent"
          }
        ]
      })
    });

    await expect(
      fetchPublicMatchDetail("legacy-contract", fetchImpl as unknown as typeof fetch)
    ).resolves.toEqual({
      match_id: "legacy-contract",
      status: "active",
      map: "britain",
      tick: 18,
      tick_interval_seconds: 45,
      current_player_count: 2,
      max_player_count: 6,
      open_slot_count: 4,
      roster: [
        {
          player_id: "player-1",
          display_name: "Arthur",
          competitor_kind: "human"
        },
        {
          player_id: "player-2",
          display_name: "Morgana",
          competitor_kind: "agent"
        }
      ]
    });
  });

  it("rejects contradictory roster identity combinations when additive fields are present", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        match_id: "broken",
        status: "active",
        map: "britain",
        tick: 18,
        tick_interval_seconds: 45,
        current_player_count: 2,
        max_player_count: 6,
        open_slot_count: 4,
        roster: [
          {
            player_id: "player-1",
            display_name: "Arthur",
            competitor_kind: "human",
            agent_id: "invented-human-agent",
            human_id: null
          },
          {
            player_id: "player-2",
            display_name: "Morgana",
            competitor_kind: "agent",
            agent_id: "agent-player-2",
            human_id: "human:should-not-be-here"
          }
        ]
      })
    });

    await expect(
      fetchPublicMatchDetail("broken", fetchImpl as unknown as typeof fetch)
    ).rejects.toEqual(
      new PublicMatchDetailError("Unable to load this public match right now.", "unavailable")
    );
  });
});


describe("fetchCompletedMatches", () => {
  it("accepts additive winner competitor summaries while preserving legacy winner display names", async () => {
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
            winning_player_display_names: ["Arthur", "Morgana"],
            winning_competitors: [
              {
                display_name: "Arthur",
                competitor_kind: "human",
                agent_id: null,
                human_id: "human:00000000-0000-0000-0000-000000000301"
              },
              {
                display_name: "Morgana",
                competitor_kind: "agent",
                agent_id: "agent-player-2",
                human_id: null
              }
            ]
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
          winning_player_display_names: ["Arthur", "Morgana"],
          winning_competitors: [
            {
              display_name: "Arthur",
              competitor_kind: "human",
              agent_id: null,
              human_id: "human:00000000-0000-0000-0000-000000000301"
            },
            {
              display_name: "Morgana",
              competitor_kind: "agent",
              agent_id: "agent-player-2",
              human_id: null
            }
          ]
        }
      ]
    });
  });

  it("rejects winner competitor summaries that invent human agent ids", async () => {
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
            winning_player_display_names: ["Arthur"],
            winning_competitors: [
              {
                display_name: "Arthur",
                competitor_kind: "human",
                agent_id: "invented-human-id",
                human_id: null
              }
            ]
          }
        ]
      })
    });

    await expect(fetchCompletedMatches(fetchImpl as unknown as typeof fetch)).rejects.toEqual(
      new CompletedMatchesError("Unable to load completed matches right now.")
    );
  });

  it("rejects winner competitor summaries that omit a human_id for human rows", async () => {
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
            winning_player_display_names: ["Arthur"],
            winning_competitors: [
              {
                display_name: "Arthur",
                competitor_kind: "human",
                agent_id: null,
                human_id: null
              }
            ]
          }
        ]
      })
    });

    await expect(fetchCompletedMatches(fetchImpl as unknown as typeof fetch)).rejects.toEqual(
      new CompletedMatchesError("Unable to load completed matches right now.")
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
            winning_player_display_names: ["Arthur", "Morgana"],
            winning_competitors: [
              {
                display_name: "Arthur",
                competitor_kind: "human",
                agent_id: null,
                human_id: "human:00000000-0000-0000-0000-000000000301"
              },
              {
                display_name: "Morgana",
                competitor_kind: "agent",
                agent_id: "agent-player-2",
                human_id: null
              }
            ]
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
          winning_player_display_names: ["Arthur", "Morgana"],
          winning_competitors: [
            {
              display_name: "Arthur",
              competitor_kind: "human",
              agent_id: null,
              human_id: "human:00000000-0000-0000-0000-000000000301"
            },
            {
              display_name: "Morgana",
              competitor_kind: "agent",
              agent_id: "agent-player-2",
              human_id: null
            }
          ]
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
