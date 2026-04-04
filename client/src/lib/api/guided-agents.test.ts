import { describe, expect, it, vi } from "vitest";
import {
  fetchOwnedAgentGuidedSession,
  GuidedAgentControlsError,
  submitOwnedAgentGuidance,
  submitOwnedAgentOverride
} from "./guided-agents";

describe("guided live client helpers", () => {
  it("fetches the owned guided-session read model through the existing bearer-token session", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        match_id: "match-alpha",
        agent_id: "agent-player-2",
        player_id: "player-2",
        state: {
          match_id: "match-alpha",
          player_id: "player-2",
          tick: 144,
          resources: {
            food: 120,
            production: 80,
            money: 200
          },
          cities: {},
          visible_armies: [],
          alliance_id: null,
          alliance_members: [],
          victory: {
            leading_alliance: null,
            cities_held: 0,
            threshold: 13,
            countdown_ticks_remaining: null
          }
        },
        queued_orders: {
          movements: [{ army_id: "army-1", destination: "york" }],
          recruitment: [],
          upgrades: [],
          transfers: []
        },
        guidance: [],
        group_chats: [],
        messages: {
          world: [],
          direct: [],
          group: []
        },
        recent_activity: {
          alliances: [],
          treaties: []
        }
      })
    });

    await expect(
      fetchOwnedAgentGuidedSession("match-alpha", "agent-player-2", "human-jwt", fetchImpl as unknown as typeof fetch, {
        apiBaseUrl: "https://session.example/"
      })
    ).resolves.toMatchObject({
      match_id: "match-alpha",
      agent_id: "agent-player-2",
      player_id: "player-2",
      queued_orders: {
        movements: [{ army_id: "army-1", destination: "york" }],
        recruitment: [],
        upgrades: [],
        transfers: []
      }
    });

    expect(fetchImpl).toHaveBeenCalledWith(
      "https://session.example/api/v1/matches/match-alpha/agents/agent-player-2/guided-session",
      {
        cache: "no-store",
        headers: {
          accept: "application/json",
          authorization: "Bearer human-jwt"
        }
      }
    );
  });

  it("posts owned guidance through the shipped route and validates the accepted contract", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      status: 202,
      json: async () => ({
        status: "accepted",
        guidance_id: "guidance-7",
        match_id: "match-alpha",
        agent_id: "agent-player-2",
        player_id: "player-2",
        tick: 144,
        content: "Hold the north and probe the coast."
      })
    });

    await expect(
      submitOwnedAgentGuidance(
        {
          match_id: "match-alpha",
          tick: 144,
          content: "Hold the north and probe the coast."
        },
        "agent-player-2",
        "human-jwt",
        fetchImpl as unknown as typeof fetch
      )
    ).resolves.toEqual({
      status: "accepted",
      guidance_id: "guidance-7",
      match_id: "match-alpha",
      agent_id: "agent-player-2",
      player_id: "player-2",
      tick: 144,
      content: "Hold the north and probe the coast."
    });
  });

  it("posts owned overrides through the shipped route using the existing order batch shape", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      status: 202,
      json: async () => ({
        status: "accepted",
        override_id: "override-3",
        match_id: "match-alpha",
        agent_id: "agent-player-2",
        player_id: "player-2",
        tick: 144,
        submission_index: 2,
        superseded_submission_count: 1,
        orders: {
          movements: [{ army_id: "army-1", destination: "york" }],
          recruitment: [],
          upgrades: [],
          transfers: []
        }
      })
    });

    await expect(
      submitOwnedAgentOverride(
        {
          match_id: "match-alpha",
          tick: 144,
          orders: {
            movements: [{ army_id: "army-1", destination: "york" }],
            recruitment: [],
            upgrades: [],
            transfers: []
          }
        },
        "agent-player-2",
        "human-jwt",
        fetchImpl as unknown as typeof fetch,
        { apiBaseUrl: "https://session.example/" }
      )
    ).resolves.toMatchObject({
      override_id: "override-3",
      superseded_submission_count: 1,
      orders: {
        movements: [{ army_id: "army-1", destination: "york" }],
        recruitment: [],
        upgrades: [],
        transfers: []
      }
    });

    expect(fetchImpl).toHaveBeenCalledWith(
      "https://session.example/api/v1/matches/match-alpha/agents/agent-player-2/override",
      {
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
            movements: [{ army_id: "army-1", destination: "york" }],
            recruitment: [],
            upgrades: [],
            transfers: []
          }
        })
      }
    );
  });

  it("surfaces structured guided write errors deterministically", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({
        error: {
          code: "guided_override_tick_mismatch",
          message: "Override payload tick '143' does not match current match tick '144'."
        }
      })
    });

    await expect(
      submitOwnedAgentOverride(
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
        "agent-player-2",
        "human-jwt",
        fetchImpl as unknown as typeof fetch
      )
    ).rejects.toMatchObject({
      message: "Override payload tick '143' does not match current match tick '144'.",
      code: "guided_override_tick_mismatch",
      statusCode: 409
    });
  });

  it("fails closed on malformed guided-session payloads", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        match_id: "match-alpha",
        agent_id: "agent-player-2"
      })
    });

    await expect(
      fetchOwnedAgentGuidedSession(
        "match-alpha",
        "agent-player-2",
        "human-jwt",
        fetchImpl as unknown as typeof fetch
      )
    ).rejects.toMatchObject({
      message: "Unable to load guided agent controls right now.",
      code: "invalid_guided_session_response",
      statusCode: 200
    });
  });
});
