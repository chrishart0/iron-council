import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { AppShell } from "./app-shell";
import { ProtectedRoute } from "./protected-route";
import { SessionProvider } from "../session/session-provider";
import { SESSION_STORAGE_KEY } from "../../lib/session-storage";

afterEach(() => {
  cleanup();
  window.localStorage.clear();
});

describe("ProtectedRoute", () => {
  it("keeps the public navigation available without authentication", async () => {
    render(
      <SessionProvider>
        <AppShell>
          <p>Public page</p>
        </AppShell>
      </SessionProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("link", { name: "Home" })).toBeVisible();
    });

    expect(screen.getByRole("link", { name: "Public matches" })).toBeVisible();
    expect(
      screen.getByRole("link", { name: "Human lobby (auth required)" })
    ).toBeVisible();
  });

  it("shows a clear configuration requirement on authenticated routes when no token exists", async () => {
    render(
      <SessionProvider>
        <ProtectedRoute title="Human lobby">
          <p>Authenticated content</p>
        </ProtectedRoute>
      </SessionProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Human lobby")).toBeVisible();
    });

    expect(screen.getByText(/requires a configured human bearer token/i)).toBeVisible();
    expect(screen.queryByText("Authenticated content")).not.toBeInTheDocument();
  });

  it("renders authenticated placeholder content when a token exists", async () => {
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    render(
      <SessionProvider>
        <ProtectedRoute title="Human lobby">
          <p>Authenticated content</p>
        </ProtectedRoute>
      </SessionProvider>
    );

    expect(screen.queryByText(/requires a configured human bearer token/i)).not.toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Authenticated content")).toBeVisible();
    });
  });
});
