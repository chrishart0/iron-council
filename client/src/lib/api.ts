import type {
  MatchListResponse,
  MatchSummary,
  PublicMatchDetailResponse,
  PublicMatchRosterRow
} from "./types";
import { DEFAULT_API_BASE_URL, normalizeApiBaseUrl } from "./session-storage";

const PUBLIC_MATCHES_ERROR_MESSAGE = "Unable to load public matches right now.";
const PUBLIC_MATCH_DETAIL_ERROR_MESSAGE = "Unable to load this public match right now.";
const PUBLIC_MATCH_DETAIL_NOT_FOUND_MESSAGE =
  "This match is unavailable. It may not exist or may already be completed.";

export class PublicMatchesError extends Error {
  constructor(message = PUBLIC_MATCHES_ERROR_MESSAGE) {
    super(message);
    this.name = "PublicMatchesError";
  }
}

export class PublicMatchDetailError extends Error {
  constructor(
    message = PUBLIC_MATCH_DETAIL_ERROR_MESSAGE,
    readonly kind: "not_found" | "unavailable" = "unavailable"
  ) {
    super(message);
    this.name = "PublicMatchDetailError";
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

export async function fetchPublicMatchDetail(
  matchId: string,
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<PublicMatchDetailResponse> {
  const response = await fetchImpl(
    `${resolveApiBaseUrl(options?.apiBaseUrl)}/api/v1/matches/${encodeURIComponent(matchId)}`,
    {
      cache: "no-store",
      headers: {
        accept: "application/json"
      }
    }
  );

  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);

    if (response.status === 404 && isApiNotFoundError(payload)) {
      throw new PublicMatchDetailError(PUBLIC_MATCH_DETAIL_NOT_FOUND_MESSAGE, "not_found");
    }

    throw new PublicMatchDetailError(PUBLIC_MATCH_DETAIL_ERROR_MESSAGE, "unavailable");
  }

  const payload: unknown = await response.json();

  if (!isPublicMatchDetailResponse(payload)) {
    throw new PublicMatchDetailError(PUBLIC_MATCH_DETAIL_ERROR_MESSAGE, "unavailable");
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

function isPublicMatchDetailResponse(payload: unknown): payload is PublicMatchDetailResponse {
  if (!isRecord(payload)) {
    return false;
  }

  if (!isMatchSummary(payload)) {
    return false;
  }

  const roster = (payload as Record<string, unknown>).roster;

  return Array.isArray(roster) && roster.every(isRosterRow);
}

function isRosterRow(payload: unknown): payload is PublicMatchRosterRow {
  if (!isRecord(payload)) {
    return false;
  }

  return (
    typeof payload.display_name === "string" &&
    (payload.competitor_kind === "human" || payload.competitor_kind === "agent")
  );
}

function isApiNotFoundError(payload: unknown): boolean {
  if (!isRecord(payload) || !isRecord(payload.error)) {
    return false;
  }

  return payload.error.code === "match_not_found";
}

function isRecord(payload: unknown): payload is Record<string, unknown> {
  return typeof payload === "object" && payload !== null;
}
