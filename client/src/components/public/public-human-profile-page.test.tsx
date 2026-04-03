import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PublicHumanProfilePage } from "./public-human-profile-page";
import { SessionProvider } from "../session/session-provider";
import { SESSION_STORAGE_KEY } from "../../lib/session-storage";

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  vi.restoreAllMocks();
});

describe("PublicHumanProfilePage", () => {
  it("shows deterministic loading first, then renders the shipped human profile payload", async () => {
    let resolveResponse!: (value: unknown) => void;
    const responsePromise = new Promise((resolve) => {
      resolveResponse = resolve;
    });

    const fetchSpy = vi.fn().mockReturnValue(responsePromise);
    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <PublicHumanProfilePage humanId="human:00000000-0000-0000-0000-000000000301" />
      </SessionProvider>
    );

    expect(screen.getByText("Loading human profile")).toBeVisible();

    resolveResponse({
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
            signed: 0,
            active: 0,
            honored: 0,
            withdrawn: 0,
            broken_by_self: 0,
            broken_by_counterparty: 0
          },
          history: []
        }
      })
    });

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Arthur" })).toBeVisible();
    });

    expect(screen.getByText("human:00000000-0000-0000-0000-000000000301")).toBeVisible();
    expect(screen.getByText("ELO 1234")).toBeVisible();
    expect(screen.getByText("Settled")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Treaty reputation" })).toBeVisible();
    expect(screen.getByText("No public treaty history has been recorded yet.")).toBeVisible();
    expect(screen.getByRole("link", { name: "Back to leaderboard" })).toHaveAttribute(
      "href",
      "/leaderboard"
    );
  });

  it("renders honored treaties as visibly final in the treaty history list", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
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
      })
    );

    render(
      <SessionProvider>
        <PublicHumanProfilePage humanId="human:00000000-0000-0000-0000-000000000301" />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Arthur" })).toBeVisible();
    });

    expect(screen.getByRole("list", { name: "Human treaty history" })).toHaveTextContent(
      "honored"
    );
    expect(screen.getByRole("list", { name: "Human treaty history" })).not.toHaveTextContent(
      "still active"
    );
  });

  it("waits for session hydration before the first human profile request", async () => {
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "https://hydrated.example/",
        bearerToken: null
      })
    );

    const fetchSpy = vi.fn().mockResolvedValue({
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
            signed: 0,
            active: 0,
            honored: 0,
            withdrawn: 0,
            broken_by_self: 0,
            broken_by_counterparty: 0
          },
          history: []
        }
      })
    });
    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <PublicHumanProfilePage humanId="human:00000000-0000-0000-0000-000000000301" />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Arthur" })).toBeVisible();
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      "https://hydrated.example/api/v1/humans/human%3A00000000-0000-0000-0000-000000000301/profile",
      {
        cache: "no-store",
        headers: {
          accept: "application/json"
        }
      }
    );
  });

  it("renders a deterministic unavailable state for missing humans", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ error: { code: "human_not_found", message: "missing" } })
      })
    );

    render(
      <SessionProvider>
        <PublicHumanProfilePage humanId="human:missing" />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Human profile unavailable");
    });

    expect(screen.getByText("This human profile is unavailable. It may not exist.")).toBeVisible();
  });
});
