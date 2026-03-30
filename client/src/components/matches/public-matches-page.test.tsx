import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PublicMatchesPage } from "./public-matches-page";
import { SessionProvider } from "../session/session-provider";
import { SESSION_STORAGE_KEY } from "../../lib/session-storage";

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  vi.restoreAllMocks();
});

describe("PublicMatchesPage", () => {
  it("waits for session hydration before the first public matches request", async () => {
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
        <PublicMatchesPage />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("No public matches yet");
    });

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(fetchSpy).toHaveBeenCalledWith("https://hydrated.example/api/v1/matches", {
      cache: "no-store",
      headers: {
        accept: "application/json"
      }
    });
  });
});
