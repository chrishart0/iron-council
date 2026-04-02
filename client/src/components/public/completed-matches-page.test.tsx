import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CompletedMatchesPage } from "./completed-matches-page";
import { SessionProvider } from "../session/session-provider";
import { SESSION_STORAGE_KEY } from "../../lib/session-storage";

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  vi.restoreAllMocks();
});

describe("CompletedMatchesPage", () => {
  it("shows a loading state first, then renders compact completed-match cards with replay links", async () => {
    let resolveResponse!: (value: unknown) => void;
    const responsePromise = new Promise((resolve) => {
      resolveResponse = resolve;
    });

    const fetchSpy = vi.fn().mockReturnValue(responsePromise);
    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <CompletedMatchesPage />
      </SessionProvider>
    );

    expect(screen.getByText("Loading completed matches")).toBeVisible();

    resolveResponse({
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
                agent_id: null
              },
              {
                display_name: "Morgana",
                competitor_kind: "agent",
                agent_id: "agent-player-2"
              }
            ]
          }
        ]
      })
    });

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Completed Matches" })).toBeVisible();
    });

    const cards = within(screen.getByRole("list", { name: "Completed match summaries" })).getAllByRole(
      "listitem"
    );

    expect(cards).toHaveLength(1);
    expect(cards[0]).toHaveTextContent("match-complete");
    expect(cards[0]).toHaveTextContent("britain");
    expect(cards[0]).toHaveTextContent("155");
    expect(cards[0]).toHaveTextContent("3");
    expect(cards[0]).toHaveTextContent("2026-03-29T08:30:00Z");
    expect(cards[0]).toHaveTextContent("Iron Crown");
    expect(cards[0]).toHaveTextContent("Arthur, Morgana");
    expect(within(cards[0]).getByRole("link", { name: "Morgana" })).toHaveAttribute(
      "href",
      "/agents/agent-player-2"
    );
    expect(within(cards[0]).queryByRole("link", { name: "Arthur" })).not.toBeInTheDocument();
    expect(within(cards[0]).getByRole("link", { name: "Open replay/history page" })).toHaveAttribute(
      "href",
      "/matches/match-complete/history"
    );
    expect(screen.queryByText(/tick snapshot/i)).not.toBeInTheDocument();
  });

  it("waits for session hydration before the first completed-match request", async () => {
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "https://hydrated.example/",
        bearerToken: null
      })
    );

    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ matches: [] })
    });
    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <CompletedMatchesPage />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("No completed matches yet");
    });

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(fetchSpy).toHaveBeenCalledWith("https://hydrated.example/api/v1/matches/completed", {
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
          code: "completed_match_summaries_unavailable",
          message: "Persisted completed matches are only available in DB-backed mode."
        }
      })
    });
    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <CompletedMatchesPage />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Completed matches unavailable");
    });

    expect(screen.getByText("Unable to load completed matches right now.")).toBeVisible();
    expect(screen.getByRole("link", { name: "Back to home" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "View public leaderboard" })).toHaveAttribute(
      "href",
      "/leaderboard"
    );
    expect(screen.queryByText(/db-backed mode/i)).not.toBeInTheDocument();
  });
});
