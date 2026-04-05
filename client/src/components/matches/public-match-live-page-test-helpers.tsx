import { cleanup, render } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";
import { loadBritainMapLayout } from "../../lib/britain-map";
import { SESSION_STORAGE_KEY } from "../../lib/session-storage";
import { PublicMatchLivePage } from "./public-match-live-page";
import { SessionProvider } from "../session/session-provider";
import { makeMatchSummaryResponse } from "./public-match-live-page-fixtures";

export class MockWebSocket {
  static instances: MockWebSocket[] = [];

  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;
  readyState = 0;

  constructor(readonly url: string) {
    MockWebSocket.instances.push(this);
  }

  emitOpen() {
    this.readyState = 1;
    this.onopen?.();
  }

  emitMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent<string>);
  }

  emitError() {
    this.onerror?.();
  }

  emitClose() {
    this.readyState = 3;
    this.onclose?.();
  }

  close() {
    this.readyState = 3;
  }
}

export function makeJsonResponse(payload: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload
  };
}

export function setStoredSpectatorSession(apiBaseUrl = "http://127.0.0.1:8000") {
  window.localStorage.setItem(
    SESSION_STORAGE_KEY,
    JSON.stringify({
      apiBaseUrl,
      bearerToken: null
    })
  );
}

export function renderPublicMatchLivePage(matchId = "match-alpha") {
  return render(
    <SessionProvider>
      <PublicMatchLivePage matchId={matchId} mapLayout={loadBritainMapLayout()} />
    </SessionProvider>
  );
}

export function stubSpectatorFetch(summary = makeMatchSummaryResponse()) {
  const fetchSpy = vi.fn().mockResolvedValue(makeJsonResponse(summary));
  vi.stubGlobal("fetch", fetchSpy);
  return fetchSpy;
}

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  vi.restoreAllMocks();
  MockWebSocket.instances = [];
});

beforeEach(() => {
  vi.stubGlobal("WebSocket", MockWebSocket);
});
