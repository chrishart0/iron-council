import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { HumanLobbyPage } from "./human-lobby-page";
import { SessionProvider } from "../session/session-provider";
import { SESSION_STORAGE_KEY } from "../../lib/session-storage";

afterEach(() => { cleanup(); window.localStorage.clear(); vi.restoreAllMocks(); });

function renderPage() {
  window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify({ apiBaseUrl: "https://hydrated.example/", bearerToken: "human-jwt" }));
  render(<SessionProvider><HumanLobbyPage /></SessionProvider>);
}

describe("HumanLobbyPage", () => {
  it("creates a lobby and renders the returned confirmed state", async () => {
    const fetchSpy = vi.fn().mockResolvedValue({ ok: true, status: 201, json: async () => ({ match_id: "match-alpha", status: "lobby", map: "britain", tick: 0, tick_interval_seconds: 20, current_player_count: 1, max_player_count: 4, open_slot_count: 3, creator_player_id: "player-1" }) });
    vi.stubGlobal("fetch", fetchSpy);
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: /create lobby/i }));
    await waitFor(() => expect(screen.getByText(/last confirmed action: create/i)).toBeVisible());
    expect(screen.getByText("match-alpha")).toBeVisible();
  });

  it("joins a lobby and keeps the last server-confirmed state deterministic", async () => {
    const fetchSpy = vi.fn().mockResolvedValue({ ok: true, status: 202, json: async () => ({ status: "accepted", match_id: "match-beta", agent_id: "human:user-1", player_id: "player-2" }) });
    vi.stubGlobal("fetch", fetchSpy);
    renderPage();
    fireEvent.change(screen.getByLabelText(/match id/i), { target: { value: "match-beta" } });
    fireEvent.click(screen.getByRole("button", { name: /join lobby/i }));
    await waitFor(() => expect(screen.getByText(/joined match-beta as player-2/i)).toBeVisible());
  });

  it("starts the last confirmed lobby through the existing start route", async () => {
    const fetchSpy = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => ({ match_id: "match-alpha", status: "lobby", map: "britain", tick: 0, tick_interval_seconds: 20, current_player_count: 1, max_player_count: 4, open_slot_count: 3, creator_player_id: "player-1" }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ match_id: "match-alpha", status: "active", map: "britain", tick: 0, tick_interval_seconds: 20, current_player_count: 2, max_player_count: 4, open_slot_count: 2 }) });
    vi.stubGlobal("fetch", fetchSpy);
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: /create lobby/i }));
    await waitFor(() => expect(screen.getByText(/last confirmed action: create/i)).toBeVisible());

    fireEvent.click(screen.getByRole("button", { name: /start lobby/i }));
    await waitFor(() => expect(screen.getByText(/last confirmed action: start/i)).toBeVisible());

    expect(fetchSpy).toHaveBeenNthCalledWith(
      2,
      "https://hydrated.example/api/v1/matches/match-alpha/start",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ authorization: "Bearer human-jwt", accept: "application/json" })
      })
    );
    expect(screen.getByText("active")).toBeVisible();
    expect(screen.getByText("2 / 4")).toBeVisible();
  });

  it("surfaces structured errors without inventing optimistic lobby state", async () => {
    const fetchSpy = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => ({ match_id: "match-alpha", status: "lobby", map: "britain", tick: 0, tick_interval_seconds: 20, current_player_count: 1, max_player_count: 4, open_slot_count: 3, creator_player_id: "player-1" }) })
      .mockResolvedValueOnce({ ok: false, status: 403, json: async () => ({ error: { code: "match_start_forbidden", message: "Authenticated human does not own lobby 'match-alpha'." } }) });
    vi.stubGlobal("fetch", fetchSpy);
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: /create lobby/i }));
    await waitFor(() => expect(screen.getByText(/last confirmed action: create/i)).toBeVisible());
    fireEvent.click(screen.getByRole("button", { name: /start lobby/i }));
    await waitFor(() => expect(screen.getByText(/authenticated human does not own lobby/i)).toBeVisible());
    expect(screen.getByText("match_start_forbidden")).toBeVisible();
    expect(screen.getByText("403")).toBeVisible();
    expect(screen.getByText(/last confirmed action: create/i)).toBeVisible();
  });
});
