import { describe, expect, it, vi } from "vitest";
import {
  fetchMatchReplayTick,
  fetchPublicMatchHistory,
  MatchReplayTickError,
  PublicMatchHistoryError
} from "./public-history";

describe("public history helper failure normalization", () => {
  const transportCases = [
    {
      name: "fetchPublicMatchHistory",
      invoke: (fetchImpl: typeof fetch) => fetchPublicMatchHistory("match-complete", fetchImpl),
      expected: new PublicMatchHistoryError("Unable to load match history right now.", "unavailable")
    },
    {
      name: "fetchMatchReplayTick",
      invoke: (fetchImpl: typeof fetch) => fetchMatchReplayTick("match-complete", 155, fetchImpl),
      expected: new MatchReplayTickError("Unable to load this replay tick right now.", "unavailable")
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

describe("fetchPublicMatchHistory", () => {
  it("accepts read-only competitor roster metadata with honest agent ids", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        match_id: "match-complete",
        status: "completed",
        current_tick: 155,
        tick_interval_seconds: 30,
        competitors: [
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
        ],
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
      competitors: [
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
      ],
      history: [{ tick: 140 }, { tick: 155 }]
    });
  });

  it("rejects history competitor rows that claim a human agent id", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        match_id: "match-complete",
        status: "completed",
        current_tick: 155,
        tick_interval_seconds: 30,
        competitors: [
          {
            display_name: "Arthur",
            competitor_kind: "human",
            agent_id: "invented-human-id",
            human_id: null
          }
        ],
        history: [{ tick: 155 }]
      })
    });

    await expect(
      fetchPublicMatchHistory("match-complete", fetchImpl as unknown as typeof fetch)
    ).rejects.toEqual(
      new PublicMatchHistoryError("Unable to load match history right now.", "unavailable")
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
        competitors: [
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
        ],
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
      competitors: [
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
      ],
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
        competitors: [],
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
