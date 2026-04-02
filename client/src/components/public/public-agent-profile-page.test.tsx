import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PublicAgentProfilePage } from "./public-agent-profile-page";
import { SessionProvider } from "../session/session-provider";
import { SESSION_STORAGE_KEY } from "../../lib/session-storage";

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  vi.restoreAllMocks();
});

describe("PublicAgentProfilePage", () => {
  it("shows deterministic loading first, then renders the shipped agent profile payload", async () => {
    let resolveResponse!: (value: unknown) => void;
    const responsePromise = new Promise((resolve) => {
      resolveResponse = resolve;
    });

    const fetchSpy = vi.fn().mockReturnValue(responsePromise);
    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <PublicAgentProfilePage agentId="agent-player-2" />
      </SessionProvider>
    );

    expect(screen.getByText("Loading agent profile")).toBeVisible();

    resolveResponse({
      ok: true,
      json: async () => ({
        agent_id: "agent-player-2",
        display_name: "Morgana",
        is_seeded: true,
        rating: {
          elo: 1211,
          provisional: false
        },
        history: {
          matches_played: 2,
          wins: 1,
          losses: 0,
          draws: 1
        }
      })
    });

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Morgana" })).toBeVisible();
    });

    expect(screen.getByText("agent-player-2")).toBeVisible();
    expect(screen.getAllByText("Seeded")).toHaveLength(2);
    expect(screen.getByText("ELO 1211")).toBeVisible();
    expect(screen.getByText("Settled")).toBeVisible();
    expect(screen.getByRole("link", { name: "Back to leaderboard" })).toHaveAttribute(
      "href",
      "/leaderboard"
    );
  });

  it("waits for session hydration before the first agent profile request", async () => {
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
        agent_id: "agent-player-2",
        display_name: "Morgana",
        is_seeded: true,
        rating: {
          elo: 1211,
          provisional: false
        },
        history: {
          matches_played: 2,
          wins: 1,
          losses: 0,
          draws: 1
        }
      })
    });
    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <PublicAgentProfilePage agentId="agent-player-2" />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Morgana" })).toBeVisible();
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      "https://hydrated.example/api/v1/agents/agent-player-2/profile",
      {
        cache: "no-store",
        headers: {
          accept: "application/json"
        }
      }
    );
  });

  it("renders a deterministic unavailable state for missing agents", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ error: { code: "agent_not_found", message: "missing" } })
      })
    );

    render(
      <SessionProvider>
        <PublicAgentProfilePage agentId="missing" />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Agent profile unavailable");
    });

    expect(screen.getByText("This agent profile is unavailable. It may not exist.")).toBeVisible();
  });
});
