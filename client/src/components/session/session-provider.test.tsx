import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { SessionProvider, useSession } from "./session-provider";
import { DEFAULT_API_BASE_URL, SESSION_STORAGE_KEY } from "../../lib/session-storage";

function SessionProbe() {
  const { apiBaseUrl, authStatusLabel, hasHydrated, isAuthenticated, setSession } = useSession();

  return (
    <div>
      <p>API: {apiBaseUrl}</p>
      <p>Status: {authStatusLabel}</p>
      <p>Hydrated: {hasHydrated ? "yes" : "no"}</p>
      <p>Authed: {isAuthenticated ? "yes" : "no"}</p>
      <button
        type="button"
        onClick={() =>
          setSession({
            apiBaseUrl: "https://iron.example",
            bearerToken: "token-123"
          })
        }
      >
        Update session
      </button>
    </div>
  );
}

afterEach(() => {
  cleanup();
  window.localStorage.clear();
});

describe("SessionProvider", () => {
  it("loads the default session when storage is empty", async () => {
    render(
      <SessionProvider>
        <SessionProbe />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(`API: ${DEFAULT_API_BASE_URL}`)).toBeVisible();
    });

    expect(screen.getByText("Hydrated: yes")).toBeVisible();
    expect(screen.getByText("Status: Public-only session")).toBeVisible();
    expect(screen.getByText("Authed: no")).toBeVisible();
  });

  it("rehydrates a saved API base URL and bearer token on mount", async () => {
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "https://hydrated.example/",
        bearerToken: "jwt-token"
      })
    );

    render(
      <SessionProvider>
        <SessionProbe />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("API: https://hydrated.example")).toBeVisible();
    });

    expect(screen.getByText("Hydrated: yes")).toBeVisible();
    expect(screen.getByText("Status: Human token configured")).toBeVisible();
    expect(screen.getByText("Authed: yes")).toBeVisible();
  });

  it("persists session updates through the shared localStorage seam", async () => {
    render(
      <SessionProvider>
        <SessionProbe />
      </SessionProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: "Update session" }));

    await waitFor(() => {
      expect(screen.getByText("API: https://iron.example")).toBeVisible();
    });

    expect(window.localStorage.getItem(SESSION_STORAGE_KEY)).toBe(
      JSON.stringify({
        apiBaseUrl: "https://iron.example",
        bearerToken: "token-123"
      })
    );
    expect(screen.getByText("Authed: yes")).toBeVisible();
  });
});
