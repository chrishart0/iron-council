import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { StoredSession } from "../lib/session-storage";
import { SessionContext } from "../components/session/session-context";
import type { SessionContextValue } from "../components/session/session-context";
import HomePage from "./page";

function renderHomePage(sessionOverride: Partial<StoredSession> = {}) {
  const session: StoredSession = {
    apiBaseUrl: "http://127.0.0.1:8000",
    bearerToken: null,
    ...sessionOverride
  };
  const value: SessionContextValue = {
    ...session,
    authStatusLabel: session.bearerToken ? "Human token configured" : "Public-only session",
    hasHydrated: true,
    isAuthenticated: session.bearerToken !== null,
    setSession: () => {}
  };

  return render(
    <SessionContext.Provider value={value}>
      <HomePage />
    </SessionContext.Provider>
  );
}

describe("HomePage", () => {
  it("distinguishes the public demo path from authenticated follow-on routes", () => {
    renderHomePage();

    expect(
      screen.getByText(/start with the public demo path: browse shipped read-only routes first/i)
    ).toBeVisible();
    expect(
      screen.getByText(/authenticated next steps need your own human bearer token/i)
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "View public matches" })).toHaveAttribute(
      "href",
      "/matches"
    );
    expect(screen.getByRole("link", { name: "View leaderboard" })).toHaveAttribute(
      "href",
      "/leaderboard"
    );
    expect(screen.getByRole("link", { name: "Browse completed matches" })).toHaveAttribute(
      "href",
      "/matches/completed"
    );
    expect(screen.getByRole("link", { name: "Open human lobby (auth required)" })).toHaveAttribute(
      "href",
      "/lobby"
    );
    expect(screen.getByText("Public demo path")).toBeVisible();
    expect(screen.getByText("Authenticated next steps")).toBeVisible();
    expect(
      screen.getByText(/human lobby for signed-in players and operators/i)
    ).toBeVisible();
    expect(
      screen.getByText(/owned api keys for agent access use that same bearer-backed session/i)
    ).toBeVisible();
  });

  it("updates the home-page guidance when a bearer token is already saved", () => {
    renderHomePage({ bearerToken: "human-jwt" });

    expect(
      screen.getByText(
        /stored bearer token ready: the same browser session can now move into the human lobby and owned api key flows/i
      )
    ).toBeVisible();
    expect(
      screen.getByText(
        /your saved bearer token is ready for the human lobby, and the session sidebar below is where you manage owned api keys for agent access/i
      )
    ).toBeVisible();
  });
});
