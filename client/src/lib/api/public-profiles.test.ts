import { describe, expect, it, vi } from "vitest";
import {
  fetchPublicAgentProfile,
  fetchPublicHumanProfile,
  fetchPublicLeaderboard,
  PublicAgentProfileError,
  PublicHumanProfileError,
  PublicLeaderboardError
} from "./public-profiles";

describe("public profile helper failure normalization", () => {
  const transportCases = [
    {
      name: "fetchPublicLeaderboard",
      invoke: (fetchImpl: typeof fetch) => fetchPublicLeaderboard(fetchImpl),
      expected: new PublicLeaderboardError("Unable to load the public leaderboard right now.")
    },
    {
      name: "fetchPublicAgentProfile",
      invoke: (fetchImpl: typeof fetch) => fetchPublicAgentProfile("agent-player-2", fetchImpl),
      expected: new PublicAgentProfileError("Unable to load this agent profile right now.", "unavailable")
    },
    {
      name: "fetchPublicHumanProfile",
      invoke: (fetchImpl: typeof fetch) =>
        fetchPublicHumanProfile("human:00000000-0000-0000-0000-000000000301", fetchImpl),
      expected: new PublicHumanProfileError("Unable to load this human profile right now.", "unavailable")
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
            agent_id: null,
            human_id: "human:00000000-0000-0000-0000-000000000301",
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
          agent_id: null,
          human_id: "human:00000000-0000-0000-0000-000000000301",
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
        leaderboard: [
          {
            rank: 1,
            display_name: "Arthur",
            competitor_kind: "human",
            agent_id: "agent-player-1",
            human_id: null,
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

    await expect(fetchPublicLeaderboard(fetchImpl as unknown as typeof fetch)).rejects.toEqual(
      new PublicLeaderboardError("Unable to load the public leaderboard right now.")
    );
  });
});


describe("fetchPublicAgentProfile", () => {
  it("returns the shipped public agent profile payload", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        agent_id: "agent-player-2",
        display_name: "Morgana",
        is_seeded: true,
        rating: {
          elo: 1211,
          provisional: false
        },
        history: {
          matches_played: 2,
          wins: 1,
          losses: 0,
          draws: 1
        },
        treaty_reputation: {
          summary: {
            signed: 3,
            active: 1,
            honored: 0,
            withdrawn: 1,
            broken_by_self: 1,
            broken_by_counterparty: 0
          },
          history: [
            {
              match_id: "match-alpha",
              counterparty_display_name: "Arthur",
              treaty_type: "trade",
              status: "withdrawn",
              signed_tick: 141,
              ended_tick: 142,
              broken_by_self: false
            }
          ]
        }
      })
    });

    await expect(
      fetchPublicAgentProfile("agent-player-2", fetchImpl as unknown as typeof fetch)
    ).resolves.toEqual({
      agent_id: "agent-player-2",
      display_name: "Morgana",
      is_seeded: true,
      rating: {
        elo: 1211,
        provisional: false
      },
      history: {
        matches_played: 2,
        wins: 1,
        losses: 0,
        draws: 1
      },
      treaty_reputation: {
        summary: {
          signed: 3,
          active: 1,
          honored: 0,
          withdrawn: 1,
          broken_by_self: 1,
          broken_by_counterparty: 0
        },
        history: [
          {
            match_id: "match-alpha",
            counterparty_display_name: "Arthur",
            treaty_type: "trade",
            status: "withdrawn",
            signed_tick: 141,
            ended_tick: 142,
            broken_by_self: false
          }
        ]
      }
    });

    expect(fetchImpl).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/agents/agent-player-2/profile",
      {
        cache: "no-store",
        headers: {
          accept: "application/json"
        }
      }
    );
  });

  it("raises a deterministic not-found error when the public API returns agent_not_found", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({
        error: {
          code: "agent_not_found",
          message: "Agent 'missing' was not found."
        }
      })
    });

    await expect(
      fetchPublicAgentProfile("missing", fetchImpl as unknown as typeof fetch)
    ).rejects.toEqual(
      new PublicAgentProfileError(
        "This agent profile is unavailable. It may not exist.",
        "not_found"
      )
    );
  });

  it("raises a deterministic unavailable error when the payload shape is invalid", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        agent_id: "agent-player-2",
        display_name: "Morgana"
      })
    });

    await expect(
      fetchPublicAgentProfile("agent-player-2", fetchImpl as unknown as typeof fetch)
    ).rejects.toEqual(
      new PublicAgentProfileError("Unable to load this agent profile right now.", "unavailable")
    );
  });

  it("rejects treaty history statuses outside the shipped literal contract", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        agent_id: "agent-player-2",
        display_name: "Morgana",
        is_seeded: true,
        rating: {
          elo: 1211,
          provisional: false
        },
        history: {
          matches_played: 2,
          wins: 1,
          losses: 0,
          draws: 1
        },
        treaty_reputation: {
          summary: {
            signed: 1,
            active: 0,
            honored: 1,
            withdrawn: 0,
            broken_by_self: 0,
            broken_by_counterparty: 0
          },
          history: [
            {
              match_id: "match-alpha",
              counterparty_display_name: "Arthur",
              treaty_type: "trade",
              status: "expired",
              signed_tick: 141,
              ended_tick: null,
              broken_by_self: false
            }
          ]
        }
      })
    });

    await expect(
      fetchPublicAgentProfile("agent-player-2", fetchImpl as unknown as typeof fetch)
    ).rejects.toEqual(
      new PublicAgentProfileError("Unable to load this agent profile right now.", "unavailable")
    );
  });
});


describe("fetchPublicHumanProfile", () => {
  it("returns the shipped public human profile payload", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        human_id: "human:00000000-0000-0000-0000-000000000301",
        display_name: "Arthur",
        rating: {
          elo: 1234,
          provisional: false
        },
        history: {
          matches_played: 1,
          wins: 1,
          losses: 0,
          draws: 0
        },
        treaty_reputation: {
          summary: {
            signed: 1,
            active: 0,
            honored: 1,
            withdrawn: 0,
            broken_by_self: 0,
            broken_by_counterparty: 0
          },
          history: [
            {
              match_id: "match-completed",
              counterparty_display_name: "Morgana",
              treaty_type: "defensive",
              status: "honored",
              signed_tick: 125,
              ended_tick: null,
              broken_by_self: false
            }
          ]
        }
      })
    });

    await expect(
      fetchPublicHumanProfile(
        "human:00000000-0000-0000-0000-000000000301",
        fetchImpl as unknown as typeof fetch
      )
    ).resolves.toEqual({
      human_id: "human:00000000-0000-0000-0000-000000000301",
      display_name: "Arthur",
      rating: {
        elo: 1234,
        provisional: false
      },
      history: {
        matches_played: 1,
        wins: 1,
        losses: 0,
        draws: 0
      },
      treaty_reputation: {
        summary: {
          signed: 1,
          active: 0,
          honored: 1,
          withdrawn: 0,
          broken_by_self: 0,
          broken_by_counterparty: 0
        },
        history: [
          {
            match_id: "match-completed",
            counterparty_display_name: "Morgana",
            treaty_type: "defensive",
            status: "honored",
            signed_tick: 125,
            ended_tick: null,
            broken_by_self: false
          }
        ]
      }
    });
  });

  it("raises a deterministic not-found error when the public API returns human_not_found", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({
        error: {
          code: "human_not_found",
          message: "Human 'missing' was not found."
        }
      })
    });

    await expect(
      fetchPublicHumanProfile("missing", fetchImpl as unknown as typeof fetch)
    ).rejects.toEqual(
      new PublicHumanProfileError(
        "This human profile is unavailable. It may not exist.",
        "not_found"
      )
    );
  });

  it("raises a deterministic unavailable error when the payload shape is invalid", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        human_id: "human:00000000-0000-0000-0000-000000000301",
        display_name: "Arthur"
      })
    });

    await expect(
      fetchPublicHumanProfile(
        "human:00000000-0000-0000-0000-000000000301",
        fetchImpl as unknown as typeof fetch
      )
    ).rejects.toEqual(
      new PublicHumanProfileError("Unable to load this human profile right now.", "unavailable")
    );
  });
});
