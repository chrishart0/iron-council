import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { SessionConfigPanel } from "./session-config-panel";
import { SessionProvider } from "./session-provider";
import { SESSION_STORAGE_KEY } from "../../lib/session-storage";

afterEach(() => {
  cleanup();
  window.localStorage.clear();
});

describe("SessionConfigPanel", () => {
  it("updates the persisted session values when the form is submitted", async () => {
    render(
      <SessionProvider>
        <SessionConfigPanel />
      </SessionProvider>
    );

    fireEvent.change(screen.getByLabelText("API base URL"), {
      target: { value: "https://browser.example/" }
    });
    fireEvent.change(screen.getByLabelText("Optional human bearer token"), {
      target: { value: "human-token" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Save session" }));

    await waitFor(() => {
      expect(screen.getByText("Saved browser session for future authenticated flows.")).toBeVisible();
    });

    expect(window.localStorage.getItem(SESSION_STORAGE_KEY)).toBe(
      JSON.stringify({
        apiBaseUrl: "https://browser.example",
        bearerToken: "human-token"
      })
    );
    expect(screen.getByDisplayValue("https://browser.example")).toBeVisible();
  });

  it("documents that public pages stay available without a configured token", () => {
    render(
      <SessionProvider>
        <SessionConfigPanel />
      </SessionProvider>
    );

    expect(screen.getByText(/public pages stay available without auth/i)).toBeVisible();
    expect(
      screen.getByText(/authenticated pages will reuse the stored token later/i)
    ).toBeVisible();
    expect(screen.queryByText(/TypeError|stack trace/i)).not.toBeInTheDocument();
  });
});
