import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MatchDetail } from "./match-detail";
import { PublicMatchDetailPage } from "./public-match-detail-page";
import { SessionProvider } from "../session/session-provider";
import { SESSION_STORAGE_KEY } from "../../lib/session-storage";

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  vi.restoreAllMocks();
});

describe("MatchDetail", () => {
  it("renders compact public metadata and the visible roster only", () => {
    const { container } = render(
      <MatchDetail
        match={{
          match_id: "match-alpha",
          status: "active",
          map: "britain",
          tick: 142,
          tick_interval_seconds: 30,
          current_player_count: 3,
          max_player_count: 5,
          open_slot_count: 2,
          roster: [
            { display_name: "Arthur", competitor_kind: "human" },
            { display_name: "Morgana", competitor_kind: "agent" }
          ]
        }}
      />
    );

    expect(screen.getByRole("heading", { name: "Public Match match-alpha" })).toBeVisible();
    expect(screen.getByText("Read-only public match metadata from the live server.")).toBeVisible();
    expect(screen.getByRole("link", { name: "Watch live spectator view" })).toHaveAttribute(
      "href",
      "/matches/match-alpha/live"
    );
    expect(screen.getByRole("link", { name: "Open authenticated player view" })).toHaveAttribute(
      "href",
      "/matches/match-alpha/play"
    );
    expect(screen.getByText("Match ID")).toBeVisible();
    expect(screen.getByText("match-alpha")).toBeVisible();
    expect(screen.getByText("active")).toBeVisible();
    expect(screen.getByText("britain")).toBeVisible();
    expect(screen.getByText("142")).toBeVisible();
    expect(screen.getByText("30s")).toBeVisible();
    expect(screen.getByText("3 / 5")).toBeVisible();
    expect(screen.getByText("2")).toBeVisible();
    expect(container.querySelector("dl[aria-label='Match metadata']")).not.toBeNull();

    const roster = screen.getByRole("list", { name: "Public roster" });
    const rows = within(roster).getAllByRole("listitem");

    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent("Arthur");
    expect(rows[0]).toHaveTextContent("Human");
    expect(rows[1]).toHaveTextContent("Morgana");
    expect(rows[1]).toHaveTextContent("Agent");

    expect(screen.queryByText(/api key/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/state snapshot/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/player id/i)).not.toBeInTheDocument();
  });

  it("renders duplicate public roster entries without React key warnings", () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <MatchDetail
        match={{
          match_id: "match-duplicate",
          status: "lobby",
          map: "britain",
          tick: 0,
          tick_interval_seconds: 30,
          current_player_count: 3,
          max_player_count: 5,
          open_slot_count: 2,
          roster: [
            { display_name: "Arthur", competitor_kind: "human" },
            { display_name: "Arthur", competitor_kind: "human" },
            { display_name: "Arthur", competitor_kind: "agent" }
          ]
        }}
      />
    );

    const rows = within(screen.getByRole("list", { name: "Public roster" })).getAllByRole("listitem");

    expect(rows).toHaveLength(3);
    expect(consoleErrorSpy).not.toHaveBeenCalledWith(
      expect.stringContaining("Each child in a list should have a unique")
    );
  });
});

describe("PublicMatchDetailPage", () => {
  it("waits for session hydration before loading the public match detail", async () => {
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
        match_id: "match-alpha",
        status: "paused",
        map: "britain",
        tick: 7,
        tick_interval_seconds: 45,
        current_player_count: 0,
        max_player_count: 5,
        open_slot_count: 5,
        roster: []
      })
    });

    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <PublicMatchDetailPage matchId="match-alpha" />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Public Match match-alpha" })).toBeVisible();
    });

    expect(fetchSpy).toHaveBeenCalledWith("https://hydrated.example/api/v1/matches/match-alpha", {
      cache: "no-store",
      headers: {
        accept: "application/json"
      }
    });
  });

  it("renders a deterministic unavailable state for unknown or completed matches", async () => {
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
        <PublicMatchDetailPage matchId="missing" />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Match unavailable");
    });

    expect(
      screen.getByText("This match is unavailable. It may not exist or may already be completed.")
    ).toBeVisible();
  });

  it("renders a deterministic generic error state for transport-safe failures", async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({
        error: {
          code: "internal_error",
          message: "private stack trace"
        }
      })
    });

    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <PublicMatchDetailPage matchId="match-alpha" />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Match unavailable");
    });

    expect(screen.getByText("Unable to load this public match right now.")).toBeVisible();
    expect(screen.queryByText(/private stack trace/i)).not.toBeInTheDocument();
  });
});
