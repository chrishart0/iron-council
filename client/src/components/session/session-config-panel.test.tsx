import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SessionConfigPanel } from "./session-config-panel";
import { SessionProvider } from "./session-provider";
import { SESSION_STORAGE_KEY } from "../../lib/session-storage";

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  vi.restoreAllMocks();
});

function renderPanelWithSession(session?: { apiBaseUrl: string; bearerToken: string | null }) {
  if (session) {
    window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
  }

  render(
    <SessionProvider>
      <SessionConfigPanel />
    </SessionProvider>
  );
}

function createDeferredFetchResponse() {
  let resolve: ((value: { ok: boolean; status: number; json: () => Promise<unknown> }) => void) | null = null;
  const promise = new Promise<{ ok: boolean; status: number; json: () => Promise<unknown> }>((nextResolve) => {
    resolve = nextResolve;
  });

  return {
    promise,
    resolve(response: { ok: boolean; status: number; json: () => Promise<unknown> }) {
      resolve?.(response);
    }
  };
}

function makeOwnedApiKeySummary(options: {
  keyId: string;
  eloRating: number;
  isActive: boolean;
  createdAt: string;
}) {
  return {
    key_id: options.keyId,
    agent_id: `agent-api-key-${options.keyId}`,
    elo_rating: options.eloRating,
    is_active: options.isActive,
    created_at: options.createdAt,
    entitlement: {
      is_entitled: true,
      grant_source: "manual" as const,
      concurrent_match_allowance: 1,
      granted_at: options.createdAt
    }
  };
}

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
    renderPanelWithSession();

    expect(screen.getByText(/public pages stay available without auth/i)).toBeVisible();
    expect(
      screen.getByText(/authenticated pages will reuse the stored token later/i)
    ).toBeVisible();
    expect(
      screen.getByText(/add a human bearer token above for owned api key management/i)
    ).toBeVisible();
    expect(screen.queryByRole("button", { name: /create api key/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/TypeError|stack trace/i)).not.toBeInTheDocument();
  });

  it("lists owned keys from the stored bearer-token session", async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          makeOwnedApiKeySummary({
            keyId: "key-alpha",
            eloRating: 1210,
            isActive: true,
            createdAt: "2026-04-03T09:00:00Z"
          }),
          makeOwnedApiKeySummary({
            keyId: "key-bravo",
            eloRating: 1190,
            isActive: false,
            createdAt: "2026-04-03T09:10:00Z"
          })
        ]
      })
    });
    vi.stubGlobal("fetch", fetchSpy);

    renderPanelWithSession({
      apiBaseUrl: "https://browser.example/",
      bearerToken: "human-jwt"
    });

    expect(screen.getByRole("button", { name: /create api key/i })).toBeDisabled();
    await waitFor(() => expect(screen.getByText("key-alpha")).toBeVisible());

    expect(screen.getByRole("button", { name: /create api key/i })).toBeEnabled();
    expect(screen.getByText("Active")).toBeVisible();
    expect(screen.getByText("Inactive")).toBeVisible();
    expect(screen.getByText("1210")).toBeVisible();
    expect(screen.getByText("2026-04-03 09:00:00 UTC")).toBeVisible();
    expect(fetchSpy).toHaveBeenCalledWith("https://browser.example/api/v1/account/api-keys", {
      cache: "no-store",
      headers: {
        accept: "application/json",
        authorization: "Bearer human-jwt"
      }
    });
  });

  it("reveals a newly created raw key once and keeps the durable list free of raw secrets after dismissal and remount", async () => {
    const fetchSpy = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ items: [] })
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({
          api_key: "iron_secret_once",
          summary: makeOwnedApiKeySummary({
            keyId: "key-charlie",
            eloRating: 1222,
            isActive: true,
            createdAt: "2026-04-03T09:20:00Z"
          })
        })
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          items: [
            makeOwnedApiKeySummary({
              keyId: "key-charlie",
              eloRating: 1222,
              isActive: true,
              createdAt: "2026-04-03T09:20:00Z"
            })
          ]
        })
      });
    vi.stubGlobal("fetch", fetchSpy);

    const session = {
      apiBaseUrl: "https://browser.example/",
      bearerToken: "human-jwt"
    };

    renderPanelWithSession(session);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: /create api key/i })).toBeEnabled()
    );

    fireEvent.click(screen.getByRole("button", { name: /create api key/i }));

    await waitFor(() => expect(screen.getByText("iron_secret_once")).toBeVisible());

    expect(fetchSpy).toHaveBeenNthCalledWith(
      2,
      "https://browser.example/api/v1/account/api-keys",
      {
        method: "POST",
        cache: "no-store",
        headers: {
          accept: "application/json",
          authorization: "Bearer human-jwt"
        }
      }
    );

    expect(
      screen.getByText(/this secret will not be shown again after this response/i)
    ).toBeVisible();
    expect(screen.getByText("key-charlie")).toBeVisible();
    expect(screen.queryAllByText("iron_secret_once")).toHaveLength(1);

    fireEvent.click(screen.getByRole("button", { name: /dismiss secret/i }));
    expect(screen.queryByText("iron_secret_once")).not.toBeInTheDocument();

    cleanup();
    renderPanelWithSession(session);

    await waitFor(() => expect(screen.getByText("key-charlie")).toBeVisible());
    expect(screen.queryByText("iron_secret_once")).not.toBeInTheDocument();
  });

  it("revokes only the targeted key row while preserving other rows and panel content", async () => {
    const fetchSpy = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          items: [
            makeOwnedApiKeySummary({
              keyId: "key-alpha",
              eloRating: 1210,
              isActive: true,
              createdAt: "2026-04-03T09:00:00Z"
            }),
            makeOwnedApiKeySummary({
              keyId: "key-bravo",
              eloRating: 1190,
              isActive: true,
              createdAt: "2026-04-03T09:10:00Z"
            })
          ]
        })
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () =>
          makeOwnedApiKeySummary({
            keyId: "key-alpha",
            eloRating: 1210,
            isActive: false,
            createdAt: "2026-04-03T09:00:00Z"
          })
      });
    vi.stubGlobal("fetch", fetchSpy);

    renderPanelWithSession({
      apiBaseUrl: "https://browser.example/",
      bearerToken: "human-jwt"
    });

    await waitFor(() => expect(screen.getByText("key-alpha")).toBeVisible());
    expect(screen.getByText("key-bravo")).toBeVisible();

    fireEvent.change(screen.getByLabelText("API base URL"), {
      target: { value: "https://browser.example/" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Save session" }));
    await waitFor(() => {
      expect(screen.getByText("Saved browser session for future authenticated flows.")).toBeVisible();
    });

    fireEvent.click(screen.getByRole("button", { name: /revoke key-alpha/i }));

    await waitFor(() => {
      const keyRows = screen.getAllByRole("listitem");
      const alphaRow = keyRows.find((row) => within(row).queryByText("key-alpha"));
      const bravoRow = keyRows.find((row) => within(row).queryByText("key-bravo"));

      expect(alphaRow).toBeDefined();
      expect(bravoRow).toBeDefined();
      expect(within(alphaRow as HTMLElement).getByText("Inactive")).toBeVisible();
      expect(within(bravoRow as HTMLElement).getByText("Active")).toBeVisible();
      expect(within(bravoRow as HTMLElement).getByRole("button", { name: /revoke key-bravo/i })).toBeEnabled();
    });

    expect(screen.getByText("Saved browser session for future authenticated flows.")).toBeVisible();
    expect(
      screen.getByText(/manage byoa agent keys with the current browser bearer token/i)
    ).toBeVisible();
    expect(screen.getByText("1190")).toBeVisible();
    expect(fetchSpy).toHaveBeenNthCalledWith(
      2,
      "https://browser.example/api/v1/account/api-keys/key-alpha",
      {
        method: "DELETE",
        cache: "no-store",
        headers: {
          accept: "application/json",
          authorization: "Bearer human-jwt"
        }
      }
    );
  });

  it("surfaces deterministic lifecycle errors without clearing the rest of the session surface", async () => {
    const fetchSpy = vi.fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 503,
        json: async () => ({
          error: {
            code: "api_keys_unavailable",
            message: "Account API keys are unavailable right now."
          }
        })
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          items: [
            makeOwnedApiKeySummary({
              keyId: "key-alpha",
              eloRating: 1210,
              isActive: true,
              createdAt: "2026-04-03T09:00:00Z"
            })
          ]
        })
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 503,
        json: async () => ({
          error: {
            code: "api_keys_unavailable",
            message: "Account API keys are unavailable right now."
          }
        })
      });
    vi.stubGlobal("fetch", fetchSpy);

    renderPanelWithSession({
      apiBaseUrl: "https://browser.example/",
      bearerToken: "human-jwt"
    });

    await waitFor(() => {
      expect(screen.getByText("Account API keys are unavailable right now.")).toBeVisible();
    });
    expect(screen.getByDisplayValue("https://browser.example")).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "Save session" }));
    await waitFor(() => {
      expect(screen.getByText("Saved browser session for future authenticated flows.")).toBeVisible();
    });

    cleanup();
    renderPanelWithSession({
      apiBaseUrl: "https://browser.example/",
      bearerToken: "human-jwt"
    });

    await waitFor(() => expect(screen.getByText("key-alpha")).toBeVisible());

    fireEvent.click(screen.getByRole("button", { name: /create api key/i }));

    await waitFor(() => {
      expect(screen.getByText("Account API keys are unavailable right now.")).toBeVisible();
    });
    expect(screen.getByText("key-alpha")).toBeVisible();
  });

  it("ignores a late create response after the saved browser session changes", async () => {
    const createResponse = createDeferredFetchResponse();
    const staleResponse = createDeferredFetchResponse();
    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          items: [
            makeOwnedApiKeySummary({
              keyId: "key-alpha",
              eloRating: 1210,
              isActive: true,
              createdAt: "2026-04-03T09:00:00Z"
            })
          ]
        })
      })
      .mockImplementationOnce(() => createResponse.promise)
      .mockImplementationOnce(() => staleResponse.promise);
    vi.stubGlobal("fetch", fetchSpy);

    renderPanelWithSession({
      apiBaseUrl: "https://browser.example/",
      bearerToken: "human-jwt-alpha"
    });

    await waitFor(() => expect(screen.getByText("key-alpha")).toBeVisible());

    fireEvent.click(screen.getByRole("button", { name: /create api key/i }));
    expect(screen.getByRole("button", { name: /creating key/i })).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Optional human bearer token"), {
      target: { value: "human-jwt-bravo" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Save session" }));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(3));

    staleResponse.resolve({
      ok: true,
      status: 200,
      json: async () => ({
        items: []
      })
    });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /create api key/i })).toBeEnabled();
    });
    expect(screen.queryByText("key-alpha")).not.toBeInTheDocument();
    expect(screen.queryByText("iron_secret_once")).not.toBeInTheDocument();

    createResponse.resolve({
        ok: true,
        status: 201,
        json: async () => ({
          api_key: "iron_secret_once",
          summary: makeOwnedApiKeySummary({
            keyId: "key-charlie",
            eloRating: 1222,
            isActive: true,
            createdAt: "2026-04-03T09:20:00Z"
          })
        })
      });

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledTimes(3);
    });
    expect(screen.queryByText("key-charlie")).not.toBeInTheDocument();
    expect(screen.queryByText("iron_secret_once")).not.toBeInTheDocument();
  });

  it("clears stale keys and ignores late list responses after the saved browser session changes", async () => {
    const staleResponse = createDeferredFetchResponse();
    const fetchSpy = vi
      .fn()
      .mockImplementationOnce(() => staleResponse.promise)
      .mockResolvedValueOnce({
        ok: false,
        status: 503,
        json: async () => ({
          error: {
            code: "api_keys_unavailable",
            message: "Account API keys are unavailable right now."
          }
        })
      });
    vi.stubGlobal("fetch", fetchSpy);

    renderPanelWithSession({
      apiBaseUrl: "https://browser.example/",
      bearerToken: "human-jwt-alpha"
    });

    fireEvent.change(screen.getByLabelText("Optional human bearer token"), {
      target: { value: "human-jwt-bravo" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Save session" }));

    await waitFor(() => {
      expect(screen.getByText("Account API keys are unavailable right now.")).toBeVisible();
    });
    expect(screen.queryByText("key-alpha")).not.toBeInTheDocument();

    staleResponse.resolve({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          makeOwnedApiKeySummary({
            keyId: "key-alpha",
            eloRating: 1210,
            isActive: true,
            createdAt: "2026-04-03T09:00:00Z"
          })
        ]
      })
    });

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledTimes(2);
    });
    expect(screen.queryByText("key-alpha")).not.toBeInTheDocument();
  });
});
