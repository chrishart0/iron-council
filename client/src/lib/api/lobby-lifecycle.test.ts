import { describe, expect, it, vi } from "vitest";
import {
  createMatchLobby,
  joinMatchLobby,
  LobbyActionError,
  startMatchLobby
} from "./lobby-lifecycle";

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
