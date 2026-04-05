import { cleanup, render } from "@testing-library/react";
import { afterEach, beforeEach, expect, vi } from "vitest";
import { loadBritainMapLayout } from "../../lib/britain-map";
import { SESSION_STORAGE_KEY } from "../../lib/session-storage";
import { makeGuidedSessionResponse } from "./human-match-live-page-fixtures";
import { HumanMatchLivePage } from "./human-match-live-page";
import { SessionProvider } from "../session/session-provider";

export class MockWebSocket {
  static instances: MockWebSocket[] = [];

  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
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

  emitClose(reason = "") {
    this.readyState = 3;
    this.onclose?.({ reason } as CloseEvent);
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

export function makeFetchSpyWithGuidedSession(...responses: ReturnType<typeof makeJsonResponse>[]) {
  const queuedResponses = [...responses];

  return vi.fn().mockImplementation(async (input: RequestInfo | URL) => {
    const url = String(input);

    if (url.endsWith("/guided-session")) {
      return makeJsonResponse(makeGuidedSessionResponse());
    }

    const nextResponse = queuedResponses.shift();
    if (nextResponse === undefined) {
      throw new Error(`Unexpected fetch call: ${url}`);
    }

    return nextResponse;
  });
}

export function expectFetchCall(
  fetchSpy: ReturnType<typeof vi.fn>,
  url: string,
  init: RequestInit,
  occurrence = 1
) {
  const matchingCalls = fetchSpy.mock.calls.filter(([calledUrl]) => String(calledUrl) === url);
  expect(matchingCalls.length).toBeGreaterThanOrEqual(occurrence);
  expect(matchingCalls[occurrence - 1]).toEqual([url, init]);
}

export function expectNoFetchCall(fetchSpy: ReturnType<typeof vi.fn>, url: string) {
  const matchingCalls = fetchSpy.mock.calls.filter(([calledUrl]) => String(calledUrl) === url);
  expect(matchingCalls).toHaveLength(0);
}

export function setStoredSession(options?: {
  apiBaseUrl?: string;
  bearerToken?: string;
}) {
  window.localStorage.setItem(
    SESSION_STORAGE_KEY,
    JSON.stringify({
      apiBaseUrl: options?.apiBaseUrl ?? "http://127.0.0.1:8000",
      bearerToken: options?.bearerToken ?? "human-jwt"
    })
  );
}

export function renderHumanMatchLivePage(matchId = "match-alpha") {
  return render(
    <SessionProvider>
      <HumanMatchLivePage matchId={matchId} mapLayout={loadBritainMapLayout()} />
    </SessionProvider>
  );
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
