import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MatchHistoryPage } from "./match-history-page";
import { SessionProvider } from "../session/session-provider";
import { SESSION_STORAGE_KEY } from "../../lib/session-storage";

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  vi.restoreAllMocks();
});

describe("MatchHistoryPage", () => {
  it("loads persisted history metadata and the selected replay tick using only the shipped public routes", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          match_id: "match-complete",
          status: "completed",
          current_tick: 155,
          tick_interval_seconds: 30,
          history: [{ tick: 140 }, { tick: 155 }]
        })
      })
      .mockResolvedValueOnce({
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
    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <MatchHistoryPage matchId="match-complete" selectedTick={null} />
      </SessionProvider>
    );

    expect(screen.getByText("Loading match history")).toBeVisible();

    await waitFor(() => {
      expect(screen.getByText(/Convoy secured/)).toBeVisible();
    });

    expect(fetchSpy).toHaveBeenCalledTimes(2);
    expect(fetchSpy).toHaveBeenNthCalledWith(
      1,
      "http://127.0.0.1:8000/api/v1/matches/match-complete/history",
      {
        cache: "no-store",
        headers: {
          accept: "application/json"
        }
      }
    );
    expect(fetchSpy).toHaveBeenNthCalledWith(
      2,
      "http://127.0.0.1:8000/api/v1/matches/match-complete/history/155",
      {
        cache: "no-store",
        headers: {
          accept: "application/json"
        }
      }
    );

    expect(screen.getByText("Match id: match-complete")).toBeVisible();
    expect(screen.getByText("Status: completed")).toBeVisible();
    expect(screen.getByText("Current tick: 155")).toBeVisible();
    expect(screen.getByText("Tick interval seconds: 30")).toBeVisible();
    expect(screen.getByText("Recorded ticks: 2")).toBeVisible();

    const tickLinks = within(screen.getByRole("list", { name: "Persisted ticks" })).getAllByRole("link");
    expect(tickLinks).toHaveLength(2);
    expect(tickLinks[0]).toHaveAttribute("href", "/matches/match-complete/history?tick=140");
    expect(tickLinks[1]).toHaveAttribute("href", "/matches/match-complete/history?tick=155");
    expect(screen.getByText("Selected tick: 155")).toBeVisible();
    expect(screen.getByText(/Convoy secured/)).toBeVisible();
    expect(screen.getByText(/army-1/)).toBeVisible();
    expect(screen.getByText(/Arthur/)).toBeVisible();
  });

  it("fetches the newly selected persisted tick when the browser route query changes", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          match_id: "match-complete",
          status: "completed",
          current_tick: 155,
          tick_interval_seconds: 30,
          history: [{ tick: 140 }, { tick: 155 }]
        })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          match_id: "match-complete",
          tick: 155,
          state_snapshot: { cities: { london: { owner: "Arthur" } } },
          orders: {},
          events: []
        })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          match_id: "match-complete",
          tick: 140,
          state_snapshot: { cities: { york: { owner: "Morgana" } } },
          orders: { movements: [{ army_id: "army-2", destination: "london" }] },
          events: { summary: ["Front shifted"] }
        })
      });
    vi.stubGlobal("fetch", fetchSpy);

    const { rerender } = render(
      <SessionProvider>
        <MatchHistoryPage matchId="match-complete" selectedTick={null} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Selected tick: 155")).toBeVisible();
    });

    rerender(
      <SessionProvider>
        <MatchHistoryPage matchId="match-complete" selectedTick={140} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Selected tick: 140")).toBeVisible();
    });

    expect(fetchSpy).toHaveBeenNthCalledWith(
      3,
      "http://127.0.0.1:8000/api/v1/matches/match-complete/history/140",
      {
        cache: "no-store",
        headers: {
          accept: "application/json"
        }
      }
    );
    expect(screen.getByText(/Front shifted/)).toBeVisible();
    expect(screen.getByText(/army-2/)).toBeVisible();
    expect(screen.getByText(/Morgana/)).toBeVisible();
  });

  it("waits for session hydration before the first history request and defaults to the newest recorded tick", async () => {
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "https://hydrated.example/",
        bearerToken: null
      })
    );

    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          match_id: "match-complete",
          status: "completed",
          current_tick: 200,
          tick_interval_seconds: 30,
          history: [{ tick: 140 }, { tick: 155 }]
        })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          match_id: "match-complete",
          tick: 155,
          state_snapshot: { cities: {} },
          orders: {},
          events: []
        })
      });
    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <MatchHistoryPage matchId="match-complete" selectedTick={null} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Selected tick: 155")).toBeVisible();
    });

    expect(fetchSpy).toHaveBeenNthCalledWith(
      1,
      "https://hydrated.example/api/v1/matches/match-complete/history",
      {
        cache: "no-store",
        headers: {
          accept: "application/json"
        }
      }
    );
    expect(fetchSpy).toHaveBeenNthCalledWith(
      2,
      "https://hydrated.example/api/v1/matches/match-complete/history/155",
      {
        cache: "no-store",
        headers: {
          accept: "application/json"
        }
      }
    );
  });

  it("renders a structured read-only error when the match history is unavailable", async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({
        error: {
          code: "match_not_found",
          message: "Match 'missing' was not found."
        }
      })
    });
    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <MatchHistoryPage matchId="missing" selectedTick={null} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Match history unavailable");
    });

    expect(
      screen.getByText("This completed match history is unavailable. It may not exist.")
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "Back to completed matches" })).toHaveAttribute(
      "href",
      "/matches/completed"
    );
    expect(screen.getByRole("link", { name: "View leaderboard" })).toHaveAttribute(
      "href",
      "/leaderboard"
    );
    expect(screen.getByRole("link", { name: "Back to home" })).toHaveAttribute("href", "/");
  });

  it("renders a structured read-only error when the DB-backed history API is unavailable", async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({
        error: {
          code: "match_history_unavailable",
          message: "Persisted match history is only available in DB-backed mode."
        }
      })
    });
    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <MatchHistoryPage matchId="match-complete" selectedTick={null} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Match history unavailable");
    });

    expect(screen.getByText("Unable to load match history right now.")).toBeVisible();
    expect(screen.getByRole("link", { name: "Back to completed matches" })).toHaveAttribute(
      "href",
      "/matches/completed"
    );
  });

  it("renders a structured replay-tick error while preserving the loaded history picker", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          match_id: "match-complete",
          status: "completed",
          current_tick: 155,
          tick_interval_seconds: 30,
          history: [{ tick: 140 }, { tick: 155 }]
        })
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({
          error: {
            code: "tick_not_found",
            message: "Tick 999 was not found."
          }
        })
      });
    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <MatchHistoryPage matchId="match-complete" selectedTick={999} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Replay tick unavailable");
    });

    expect(screen.getByText("Selected tick: 999")).toBeVisible();
    expect(screen.getByText("This replay tick is unavailable for the selected match.")).toBeVisible();
    expect(screen.getByRole("list", { name: "Persisted ticks" })).toBeVisible();
  });
});
