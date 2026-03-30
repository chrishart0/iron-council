import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchPublicMatches, PublicMatchesError } from "./api";

afterEach(() => {
  delete process.env.IRON_COUNCIL_API_BASE_URL;
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

  it("uses the configured API base URL without leaking a trailing slash", async () => {
    process.env.IRON_COUNCIL_API_BASE_URL = "https://iron.example/";
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ matches: [] })
    });

    await fetchPublicMatches(fetchImpl as unknown as typeof fetch);

    expect(fetchImpl).toHaveBeenCalledWith("https://iron.example/api/v1/matches", {
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
