import type {
  CompletedMatchSummary,
  CompletedMatchSummaryListResponse,
  MatchListResponse,
  MatchSummary,
  PublicMatchDetailResponse,
  PublicMatchRosterRow
} from "../types";
import { isRecord, resolveApiBaseUrl } from "./public-contract-shared";

const PUBLIC_MATCHES_ERROR_MESSAGE = "Unable to load public matches right now.";
const PUBLIC_MATCH_DETAIL_ERROR_MESSAGE = "Unable to load this public match right now.";
const COMPLETED_MATCHES_ERROR_MESSAGE = "Unable to load completed matches right now.";
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

export class CompletedMatchesError extends Error {
  constructor(message = COMPLETED_MATCHES_ERROR_MESSAGE) {
    super(message);
    this.name = "CompletedMatchesError";
  }
}

export async function fetchPublicMatches(
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<MatchListResponse> {
  try {
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
  } catch (error) {
    throw coercePublicMatchesError(error);
  }
}

export async function fetchPublicMatchDetail(
  matchId: string,
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<PublicMatchDetailResponse> {
  try {
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
  } catch (error) {
    throw coercePublicMatchDetailError(error);
  }
}

export async function fetchCompletedMatches(
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<CompletedMatchSummaryListResponse> {
  try {
    const response = await fetchImpl(
      `${resolveApiBaseUrl(options?.apiBaseUrl)}/api/v1/matches/completed`,
      {
        cache: "no-store",
        headers: {
          accept: "application/json"
        }
      }
    );

    if (!response.ok) {
      throw new CompletedMatchesError();
    }

    const payload: unknown = await response.json();

    if (!isCompletedMatchSummaryListResponse(payload)) {
      throw new CompletedMatchesError();
    }

    return {
      matches: payload.matches.map((match) => ({
        ...match,
        winning_competitors: Array.isArray(match.winning_competitors) ? match.winning_competitors : []
      }))
    };
  } catch (error) {
    throw coerceCompletedMatchesError(error);
  }
}

function coercePublicMatchesError(error: unknown): PublicMatchesError {
  return error instanceof PublicMatchesError ? error : new PublicMatchesError();
}

function coercePublicMatchDetailError(error: unknown): PublicMatchDetailError {
  return error instanceof PublicMatchDetailError
    ? error
    : new PublicMatchDetailError(PUBLIC_MATCH_DETAIL_ERROR_MESSAGE, "unavailable");
}

function coerceCompletedMatchesError(error: unknown): CompletedMatchesError {
  return error instanceof CompletedMatchesError ? error : new CompletedMatchesError();
}

function isMatchListResponse(payload: unknown): payload is MatchListResponse {
  if (!isRecord(payload) || !Array.isArray(payload.matches)) {
    return false;
  }

  return payload.matches.every(isMatchSummary);
}

function isCompletedMatchSummaryListResponse(
  payload: unknown
): payload is CompletedMatchSummaryListResponse {
  if (!isRecord(payload) || !Array.isArray(payload.matches)) {
    return false;
  }

  return payload.matches.every(isCompletedMatchSummary);
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

function isCompletedMatchSummary(payload: unknown): payload is CompletedMatchSummary {
  if (!isRecord(payload)) {
    return false;
  }

  return (
    typeof payload.match_id === "string" &&
    typeof payload.map === "string" &&
    typeof payload.final_tick === "number" &&
    typeof payload.tick_interval_seconds === "number" &&
    typeof payload.player_count === "number" &&
    typeof payload.completed_at === "string" &&
    (typeof payload.winning_alliance_name === "string" || payload.winning_alliance_name === null) &&
    Array.isArray(payload.winning_player_display_names) &&
    payload.winning_player_display_names.every((entry) => typeof entry === "string") &&
    (payload.winning_competitors === undefined ||
      (Array.isArray(payload.winning_competitors) &&
        payload.winning_competitors.every(isPublicCompetitorSummary)))
  );
}

function isPublicCompetitorSummary(payload: unknown): payload is {
  display_name: string;
  competitor_kind: "human" | "agent";
  agent_id: string | null;
  human_id: string | null;
} {
  if (!isRecord(payload)) {
    return false;
  }

  const hasValidSharedFields =
    typeof payload.display_name === "string" &&
    (payload.competitor_kind === "human" || payload.competitor_kind === "agent");

  if (!hasValidSharedFields) {
    return false;
  }

  if (payload.competitor_kind === "human") {
    return payload.agent_id === null && typeof payload.human_id === "string";
  }

  return typeof payload.agent_id === "string" && payload.human_id === null;
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

  const hasValidSharedFields =
    typeof payload.player_id === "string" &&
    typeof payload.display_name === "string" &&
    (payload.competitor_kind === "human" || payload.competitor_kind === "agent");

  if (!hasValidSharedFields) {
    return false;
  }

  const hasAgentIdentityField = Object.hasOwn(payload, "agent_id");
  const hasHumanIdentityField = Object.hasOwn(payload, "human_id");

  if (!hasAgentIdentityField && !hasHumanIdentityField) {
    return true;
  }

  if (payload.competitor_kind === "human") {
    return payload.agent_id === null && typeof payload.human_id === "string";
  }

  return typeof payload.agent_id === "string" && payload.human_id === null;
}

function isApiNotFoundError(payload: unknown): boolean {
  if (!isRecord(payload) || !isRecord(payload.error)) {
    return false;
  }

  return payload.error.code === "match_not_found";
}
