import { describe, expect, it, vi } from "vitest";
import {
  ApiKeyLifecycleError,
  buildAuthenticatedHeaders,
  buildAuthenticatedJsonHeaders,
  buildPlayerMatchWebSocketUrl,
  buildSpectatorMatchWebSocketUrl,
  createOwnedApiKey,
  fetchOwnedApiKeys,
  getPlayerWebSocketCloseMessage,
  isApiErrorEnvelope,
  isRecord,
  resolveApiBaseUrl,
  revokeOwnedApiKey
} from "./account-session";

describe("owned api key lifecycle helpers", () => {
  it("lists owned api key summaries through the existing bearer-token session", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          {
            key_id: "key-alpha",
            agent_id: "agent-api-key-key-alpha",
            elo_rating: 1210,
            is_active: true,
            created_at: "2026-04-03T09:00:00Z",
            entitlement: {
              is_entitled: true,
              grant_source: "manual",
              concurrent_match_allowance: 1,
              granted_at: "2026-04-03T09:00:00Z"
            }
          }
        ]
      })
    });

    await expect(
      fetchOwnedApiKeys("human-jwt", fetchImpl as unknown as typeof fetch, {
        apiBaseUrl: "https://session.example/"
      })
    ).resolves.toEqual({
      items: [
        {
          key_id: "key-alpha",
          agent_id: "agent-api-key-key-alpha",
          elo_rating: 1210,
          is_active: true,
          created_at: "2026-04-03T09:00:00Z",
          entitlement: {
            is_entitled: true,
            grant_source: "manual",
            concurrent_match_allowance: 1,
            granted_at: "2026-04-03T09:00:00Z"
          }
        }
      ]
    });

    expect(fetchImpl).toHaveBeenCalledWith("https://session.example/api/v1/account/api-keys", {
      cache: "no-store",
      headers: {
        accept: "application/json",
        authorization: "Bearer human-jwt"
      }
    });
  });

  it("returns the one-time raw secret only from the create response", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({
        api_key: "iron_secret_once",
        summary: {
          key_id: "key-bravo",
          agent_id: "agent-api-key-key-bravo",
          elo_rating: 1190,
          is_active: true,
          created_at: "2026-04-03T09:05:00Z",
          entitlement: {
            is_entitled: true,
            grant_source: "manual",
            concurrent_match_allowance: 1,
            granted_at: "2026-04-03T09:00:00Z"
          }
        }
      })
    });

    await expect(
      createOwnedApiKey("human-jwt", fetchImpl as unknown as typeof fetch)
    ).resolves.toEqual({
      api_key: "iron_secret_once",
      summary: {
        key_id: "key-bravo",
        agent_id: "agent-api-key-key-bravo",
        elo_rating: 1190,
        is_active: true,
        created_at: "2026-04-03T09:05:00Z",
        entitlement: {
          is_entitled: true,
          grant_source: "manual",
          concurrent_match_allowance: 1,
          granted_at: "2026-04-03T09:00:00Z"
        }
      }
    });

    expect(fetchImpl).toHaveBeenCalledWith("http://127.0.0.1:8000/api/v1/account/api-keys", {
      method: "POST",
      cache: "no-store",
      headers: {
        accept: "application/json",
        authorization: "Bearer human-jwt"
      }
    });
  });

  it("returns the inactive summary after revoke without changing the contract shape", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        key_id: "key-charlie",
        agent_id: "agent-api-key-key-charlie",
        elo_rating: 1175,
        is_active: false,
        created_at: "2026-04-03T09:07:00Z",
        entitlement: {
          is_entitled: true,
          grant_source: "manual",
          concurrent_match_allowance: 1,
          granted_at: "2026-04-03T09:00:00Z"
        }
      })
    });

    await expect(
      revokeOwnedApiKey("key-charlie", "human-jwt", fetchImpl as unknown as typeof fetch, {
        apiBaseUrl: "https://session.example/"
      })
    ).resolves.toEqual({
      key_id: "key-charlie",
      agent_id: "agent-api-key-key-charlie",
      elo_rating: 1175,
      is_active: false,
      created_at: "2026-04-03T09:07:00Z",
      entitlement: {
        is_entitled: true,
        grant_source: "manual",
        concurrent_match_allowance: 1,
        granted_at: "2026-04-03T09:00:00Z"
      }
    });

    expect(fetchImpl).toHaveBeenCalledWith(
      "https://session.example/api/v1/account/api-keys/key-charlie",
      {
        method: "DELETE",
        cache: "no-store",
        headers: {
          accept: "application/json",
          authorization: "Bearer human-jwt"
        }
      }
    );
  });

  it("surfaces structured lifecycle errors deterministically", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({
        error: {
          code: "api_keys_unavailable",
          message: "Account API keys are unavailable right now."
        }
      })
    });

    await expect(fetchOwnedApiKeys("human-jwt", fetchImpl as unknown as typeof fetch)).rejects.toEqual(
      new ApiKeyLifecycleError("Account API keys are unavailable right now.", "api_keys_unavailable", 503)
    );
  });

  it("fails closed on malformed lifecycle success payloads", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({
        api_key: "iron_secret_once",
        summary: {
          key_id: 12,
          is_active: true
        }
      })
    });

    await expect(createOwnedApiKey("human-jwt", fetchImpl as unknown as typeof fetch)).rejects.toEqual(
      new ApiKeyLifecycleError(
        "Unable to manage account API keys right now.",
        "invalid_api_key_lifecycle_response",
        201
      )
    );
  });

  it("fails closed when a successful lifecycle response body is not valid json", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => {
        throw new SyntaxError("Unexpected token < in JSON");
      }
    });

    await expect(fetchOwnedApiKeys("human-jwt", fetchImpl as unknown as typeof fetch)).rejects.toEqual(
      new ApiKeyLifecycleError(
        "Unable to manage account API keys right now.",
        "invalid_api_key_lifecycle_response",
        200
      )
    );
  });

  it("maps network failures to the shared lifecycle error", async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new Error("socket closed"));

    await expect(revokeOwnedApiKey("key-charlie", "human-jwt", fetchImpl as unknown as typeof fetch)).rejects.toEqual(
      new ApiKeyLifecycleError("Unable to manage account API keys right now.", "api_key_lifecycle_unavailable", 500)
    );
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
