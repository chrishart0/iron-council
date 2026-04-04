import { describe, expect, it, vi } from "vitest";
import {
  CommandSubmissionError,
  DiplomacySubmissionError,
  GroupChatCreateError,
  MessageSubmissionError,
  submitAllianceAction,
  submitGroupChatCreate,
  submitGroupChatMessage,
  submitMatchMessage,
  submitMatchOrders,
  submitTreatyAction
} from "./match-writes";

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
