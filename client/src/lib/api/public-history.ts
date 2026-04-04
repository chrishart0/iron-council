import type {
  MatchHistoryEntry,
  MatchReplayTickResponse,
  PublicMatchHistoryResponse,
  ReplayFieldRecord,
  ReplayFieldValue
} from "../types";
import { hasApiErrorCode, isRecord, resolveApiBaseUrl } from "./public-contract-shared";

const PUBLIC_MATCH_HISTORY_ERROR_MESSAGE = "Unable to load match history right now.";
const PUBLIC_MATCH_HISTORY_NOT_FOUND_MESSAGE =
  "This completed match history is unavailable. It may not exist.";
const MATCH_REPLAY_TICK_ERROR_MESSAGE = "Unable to load this replay tick right now.";
const MATCH_REPLAY_TICK_NOT_FOUND_MESSAGE =
  "This replay tick is unavailable for the selected match.";

export class PublicMatchHistoryError extends Error {
  constructor(
    message = PUBLIC_MATCH_HISTORY_ERROR_MESSAGE,
    readonly kind: "not_found" | "unavailable" = "unavailable"
  ) {
    super(message);
    this.name = "PublicMatchHistoryError";
  }
}

export class MatchReplayTickError extends Error {
  constructor(
    message = MATCH_REPLAY_TICK_ERROR_MESSAGE,
    readonly kind: "match_not_found" | "tick_not_found" | "unavailable" = "unavailable"
  ) {
    super(message);
    this.name = "MatchReplayTickError";
  }
}

export async function fetchPublicMatchHistory(
  matchId: string,
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<PublicMatchHistoryResponse> {
  try {
    const response = await fetchImpl(
      `${resolveApiBaseUrl(options?.apiBaseUrl)}/api/v1/matches/${encodeURIComponent(matchId)}/history`,
      {
        cache: "no-store",
        headers: {
          accept: "application/json"
        }
      }
    );

    if (!response.ok) {
      const payload: unknown = await response.json().catch(() => null);

      if (response.status === 404 && hasApiErrorCode(payload, "match_not_found")) {
        throw new PublicMatchHistoryError(PUBLIC_MATCH_HISTORY_NOT_FOUND_MESSAGE, "not_found");
      }

      throw new PublicMatchHistoryError(PUBLIC_MATCH_HISTORY_ERROR_MESSAGE, "unavailable");
    }

    const payload: unknown = await response.json();

    if (!isPublicMatchHistoryResponse(payload)) {
      throw new PublicMatchHistoryError(PUBLIC_MATCH_HISTORY_ERROR_MESSAGE, "unavailable");
    }

    return {
      ...payload,
      competitors: Array.isArray(payload.competitors) ? payload.competitors : []
    };
  } catch (error) {
    throw coercePublicMatchHistoryError(error);
  }
}

export async function fetchMatchReplayTick(
  matchId: string,
  tick: number,
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<MatchReplayTickResponse> {
  try {
    const response = await fetchImpl(
      `${resolveApiBaseUrl(options?.apiBaseUrl)}/api/v1/matches/${encodeURIComponent(matchId)}/history/${tick}`,
      {
        cache: "no-store",
        headers: {
          accept: "application/json"
        }
      }
    );

    if (!response.ok) {
      const payload: unknown = await response.json().catch(() => null);

      if (response.status === 404 && hasApiErrorCode(payload, "tick_not_found")) {
        throw new MatchReplayTickError(MATCH_REPLAY_TICK_NOT_FOUND_MESSAGE, "tick_not_found");
      }

      if (response.status === 404 && hasApiErrorCode(payload, "match_not_found")) {
        throw new MatchReplayTickError(PUBLIC_MATCH_HISTORY_NOT_FOUND_MESSAGE, "match_not_found");
      }

      throw new MatchReplayTickError(MATCH_REPLAY_TICK_ERROR_MESSAGE, "unavailable");
    }

    const payload: unknown = await response.json();

    if (!isMatchReplayTickResponse(payload)) {
      throw new MatchReplayTickError(MATCH_REPLAY_TICK_ERROR_MESSAGE, "unavailable");
    }

    return payload;
  } catch (error) {
    throw coerceMatchReplayTickError(error);
  }
}

function coercePublicMatchHistoryError(error: unknown): PublicMatchHistoryError {
  return error instanceof PublicMatchHistoryError
    ? error
    : new PublicMatchHistoryError(PUBLIC_MATCH_HISTORY_ERROR_MESSAGE, "unavailable");
}

function coerceMatchReplayTickError(error: unknown): MatchReplayTickError {
  return error instanceof MatchReplayTickError
    ? error
    : new MatchReplayTickError(MATCH_REPLAY_TICK_ERROR_MESSAGE, "unavailable");
}

function isPublicMatchHistoryResponse(payload: unknown): payload is PublicMatchHistoryResponse {
  return (
    isRecord(payload) &&
    typeof payload.match_id === "string" &&
    typeof payload.status === "string" &&
    typeof payload.current_tick === "number" &&
    typeof payload.tick_interval_seconds === "number" &&
    (payload.competitors === undefined ||
      (Array.isArray(payload.competitors) && payload.competitors.every(isPublicCompetitorSummary))) &&
    Array.isArray(payload.history) &&
    payload.history.every(isMatchHistoryEntry)
  );
}

function isMatchHistoryEntry(payload: unknown): payload is MatchHistoryEntry {
  return isRecord(payload) && typeof payload.tick === "number";
}

function isMatchReplayTickResponse(payload: unknown): payload is MatchReplayTickResponse {
  return (
    isRecord(payload) &&
    typeof payload.match_id === "string" &&
    typeof payload.tick === "number" &&
    isReplayFieldRecord(payload.state_snapshot) &&
    isReplayFieldRecord(payload.orders) &&
    (isReplayFieldRecord(payload.events) ||
      (Array.isArray(payload.events) && payload.events.every(isReplayFieldRecord)))
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

function isReplayFieldRecord(payload: unknown): payload is ReplayFieldRecord {
  return isRecord(payload) && !Array.isArray(payload) && Object.values(payload).every(isReplayFieldValue);
}

function isReplayFieldValue(payload: unknown): payload is ReplayFieldValue {
  return (
    payload === null ||
    typeof payload === "string" ||
    typeof payload === "number" ||
    typeof payload === "boolean" ||
    (Array.isArray(payload) && payload.every(isReplayFieldValue)) ||
    isReplayFieldRecord(payload)
  );
}
