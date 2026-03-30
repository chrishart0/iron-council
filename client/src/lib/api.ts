import type { MatchListResponse, MatchSummary } from "./types";
import { DEFAULT_API_BASE_URL, normalizeApiBaseUrl } from "./session-storage";

const PUBLIC_MATCHES_ERROR_MESSAGE = "Unable to load public matches right now.";

export class PublicMatchesError extends Error {
  constructor(message = PUBLIC_MATCHES_ERROR_MESSAGE) {
    super(message);
    this.name = "PublicMatchesError";
  }
}

export async function fetchPublicMatches(
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<MatchListResponse> {
  const response = await fetchImpl(`${resolveApiBaseUrl(options?.apiBaseUrl)}/api/v1/matches`, {
    cache: "no-store",
    headers: {
      accept: "application/json"
    }
  });

  if (!response.ok) {
    throw new PublicMatchesError();
  }

  const payload: unknown = await response.json();

  if (!isMatchListResponse(payload)) {
    throw new PublicMatchesError();
  }

  return payload;
}

function resolveApiBaseUrl(explicitBaseUrl?: string): string {
  if (explicitBaseUrl) {
    return normalizeApiBaseUrl(explicitBaseUrl);
  }

  return DEFAULT_API_BASE_URL;
}

function isMatchListResponse(payload: unknown): payload is MatchListResponse {
  if (!isRecord(payload) || !Array.isArray(payload.matches)) {
    return false;
  }

  return payload.matches.every(isMatchSummary);
}

function isMatchSummary(payload: unknown): payload is MatchSummary {
  if (!isRecord(payload)) {
    return false;
  }

  return (
    typeof payload.match_id === "string" &&
    typeof payload.status === "string" &&
    typeof payload.map === "string" &&
    typeof payload.tick === "number" &&
    typeof payload.tick_interval_seconds === "number" &&
    typeof payload.current_player_count === "number" &&
    typeof payload.max_player_count === "number" &&
    typeof payload.open_slot_count === "number"
  );
}

function isRecord(payload: unknown): payload is Record<string, unknown> {
  return typeof payload === "object" && payload !== null;
}
