import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PublicLeaderboardPage } from "./public-leaderboard-page";
import { SessionProvider } from "../session/session-provider";
import { SESSION_STORAGE_KEY } from "../../lib/session-storage";

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  vi.restoreAllMocks();
});

describe("PublicLeaderboardPage", () => {
  it("shows a loading state first, then renders the shipped leaderboard rows in order", async () => {
    let resolveResponse!: (value: unknown) => void;
    const responsePromise = new Promise((resolve) => {
      resolveResponse = resolve;
    });

    const fetchSpy = vi.fn().mockReturnValue(responsePromise);
    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <PublicLeaderboardPage />
      </SessionProvider>
    );

    expect(screen.getByText("Loading public leaderboard")).toBeVisible();

    resolveResponse({
      ok: true,
      json: async () => ({
        leaderboard: [
          {
            rank: 1,
            display_name: "Arthur",
            competitor_kind: "human",
            agent_id: null,
            elo: 1210,
            provisional: true,
            matches_played: 1,
            wins: 1,
            losses: 0,
            draws: 0
          },
          {
            rank: 2,
            display_name: "Morgana",
            competitor_kind: "agent",
            agent_id: "agent-player-2",
            elo: 1190,
            provisional: true,
            matches_played: 2,
            wins: 1,
            losses: 0,
            draws: 1
          }
        ]
      })
    });

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Public Leaderboard" })).toBeVisible();
    });

    const rows = within(screen.getByRole("list", { name: "Leaderboard standings" })).getAllByRole(
      "listitem"
    );

    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent("1");
    expect(rows[0]).toHaveTextContent("Arthur");
    expect(rows[0]).toHaveTextContent("Human");
    expect(rows[0]).toHaveTextContent("1210");
    expect(within(rows[0]).queryByRole("link", { name: /Arthur/ })).toBeNull();
    expect(rows[1]).toHaveTextContent("2");
    expect(rows[1]).toHaveTextContent("Morgana");
    expect(rows[1]).toHaveTextContent("Agent");
    expect(rows[1]).toHaveTextContent("1190");
    expect(within(rows[1]).getByRole("link", { name: "2. Morgana" })).toHaveAttribute(
      "href",
      "/agents/agent-player-2"
    );
  });

  it("waits for session hydration before the first leaderboard request", async () => {
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "https://hydrated.example/",
        bearerToken: null
      })
    );

    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ leaderboard: [] })
    });
    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <PublicLeaderboardPage />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("No public leaderboard rows yet");
    });

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(fetchSpy).toHaveBeenCalledWith("https://hydrated.example/api/v1/leaderboard", {
      cache: "no-store",
      headers: {
        accept: "application/json"
      }
    });
  });

  it("renders a deterministic read-only error state with stable navigation", async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({
        error: {
          code: "leaderboard_unavailable",
          message: "Persisted leaderboard is only available in DB-backed mode."
        }
      })
    });
    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <PublicLeaderboardPage />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Leaderboard unavailable");
    });

    expect(screen.getByText("Unable to load the public leaderboard right now.")).toBeVisible();
    expect(screen.getByRole("link", { name: "Back to home" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Browse completed matches" })).toHaveAttribute(
      "href",
      "/matches/completed"
    );
    expect(screen.queryByText(/db-backed mode/i)).not.toBeInTheDocument();
  });
});
