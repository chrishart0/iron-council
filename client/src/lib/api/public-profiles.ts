import type {
  AgentProfileHistory,
  AgentProfileRating,
  LeaderboardEntry,
  PublicAgentProfileResponse,
  PublicHumanProfileResponse,
  PublicLeaderboardResponse,
  TreatyHistoryRecord,
  TreatyReputation,
  TreatyReputationSummary
} from "../types";
import { hasApiErrorCode, isRecord, resolveApiBaseUrl } from "./public-contract-shared";

const PUBLIC_LEADERBOARD_ERROR_MESSAGE = "Unable to load the public leaderboard right now.";
const PUBLIC_AGENT_PROFILE_ERROR_MESSAGE = "Unable to load this agent profile right now.";
const PUBLIC_HUMAN_PROFILE_ERROR_MESSAGE = "Unable to load this human profile right now.";
const PUBLIC_AGENT_PROFILE_NOT_FOUND_MESSAGE =
  "This agent profile is unavailable. It may not exist.";
const PUBLIC_HUMAN_PROFILE_NOT_FOUND_MESSAGE =
  "This human profile is unavailable. It may not exist.";

export class PublicLeaderboardError extends Error {
  constructor(message = PUBLIC_LEADERBOARD_ERROR_MESSAGE) {
    super(message);
    this.name = "PublicLeaderboardError";
  }
}

export class PublicAgentProfileError extends Error {
  constructor(
    message = PUBLIC_AGENT_PROFILE_ERROR_MESSAGE,
    readonly kind: "not_found" | "unavailable" = "unavailable"
  ) {
    super(message);
    this.name = "PublicAgentProfileError";
  }
}

export class PublicHumanProfileError extends Error {
  constructor(
    message = PUBLIC_HUMAN_PROFILE_ERROR_MESSAGE,
    readonly kind: "not_found" | "unavailable" = "unavailable"
  ) {
    super(message);
    this.name = "PublicHumanProfileError";
  }
}

export async function fetchPublicLeaderboard(
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<PublicLeaderboardResponse> {
  try {
    const response = await fetchImpl(`${resolveApiBaseUrl(options?.apiBaseUrl)}/api/v1/leaderboard`, {
      cache: "no-store",
      headers: {
        accept: "application/json"
      }
    });

    if (!response.ok) {
      throw new PublicLeaderboardError();
    }

    const payload: unknown = await response.json();

    if (!isPublicLeaderboardResponse(payload)) {
      throw new PublicLeaderboardError();
    }

    return payload;
  } catch (error) {
    throw coercePublicLeaderboardError(error);
  }
}

export async function fetchPublicAgentProfile(
  agentId: string,
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<PublicAgentProfileResponse> {
  try {
    const response = await fetchImpl(
      `${resolveApiBaseUrl(options?.apiBaseUrl)}/api/v1/agents/${encodeURIComponent(agentId)}/profile`,
      {
        cache: "no-store",
        headers: {
          accept: "application/json"
        }
      }
    );

    if (!response.ok) {
      const payload: unknown = await response.json().catch(() => null);

      if (response.status === 404 && hasApiErrorCode(payload, "agent_not_found")) {
        throw new PublicAgentProfileError(PUBLIC_AGENT_PROFILE_NOT_FOUND_MESSAGE, "not_found");
      }

      throw new PublicAgentProfileError(PUBLIC_AGENT_PROFILE_ERROR_MESSAGE, "unavailable");
    }

    const payload: unknown = await response.json();

    if (!isPublicAgentProfileResponse(payload)) {
      throw new PublicAgentProfileError(PUBLIC_AGENT_PROFILE_ERROR_MESSAGE, "unavailable");
    }

    return payload;
  } catch (error) {
    throw coercePublicAgentProfileError(error);
  }
}

export async function fetchPublicHumanProfile(
  humanId: string,
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<PublicHumanProfileResponse> {
  try {
    const response = await fetchImpl(
      `${resolveApiBaseUrl(options?.apiBaseUrl)}/api/v1/humans/${encodeURIComponent(humanId)}/profile`,
      {
        cache: "no-store",
        headers: {
          accept: "application/json"
        }
      }
    );

    if (!response.ok) {
      const payload: unknown = await response.json().catch(() => null);

      if (response.status === 404 && hasApiErrorCode(payload, "human_not_found")) {
        throw new PublicHumanProfileError(PUBLIC_HUMAN_PROFILE_NOT_FOUND_MESSAGE, "not_found");
      }

      throw new PublicHumanProfileError(PUBLIC_HUMAN_PROFILE_ERROR_MESSAGE, "unavailable");
    }

    const payload: unknown = await response.json();

    if (!isPublicHumanProfileResponse(payload)) {
      throw new PublicHumanProfileError(PUBLIC_HUMAN_PROFILE_ERROR_MESSAGE, "unavailable");
    }

    return payload;
  } catch (error) {
    throw coercePublicHumanProfileError(error);
  }
}

function coercePublicLeaderboardError(error: unknown): PublicLeaderboardError {
  return error instanceof PublicLeaderboardError ? error : new PublicLeaderboardError();
}

function coercePublicAgentProfileError(error: unknown): PublicAgentProfileError {
  return error instanceof PublicAgentProfileError
    ? error
    : new PublicAgentProfileError(PUBLIC_AGENT_PROFILE_ERROR_MESSAGE, "unavailable");
}

function coercePublicHumanProfileError(error: unknown): PublicHumanProfileError {
  return error instanceof PublicHumanProfileError
    ? error
    : new PublicHumanProfileError(PUBLIC_HUMAN_PROFILE_ERROR_MESSAGE, "unavailable");
}

function isPublicLeaderboardResponse(payload: unknown): payload is PublicLeaderboardResponse {
  if (!isRecord(payload) || !Array.isArray(payload.leaderboard)) {
    return false;
  }

  return payload.leaderboard.every(isLeaderboardEntry);
}

function isPublicAgentProfileResponse(payload: unknown): payload is PublicAgentProfileResponse {
  return (
    isRecord(payload) &&
    typeof payload.agent_id === "string" &&
    typeof payload.display_name === "string" &&
    typeof payload.is_seeded === "boolean" &&
    isAgentProfileRating(payload.rating) &&
    isAgentProfileHistory(payload.history) &&
    isTreatyReputation(payload.treaty_reputation)
  );
}

function isPublicHumanProfileResponse(payload: unknown): payload is PublicHumanProfileResponse {
  return (
    isRecord(payload) &&
    typeof payload.human_id === "string" &&
    typeof payload.display_name === "string" &&
    isAgentProfileRating(payload.rating) &&
    isAgentProfileHistory(payload.history) &&
    isTreatyReputation(payload.treaty_reputation)
  );
}

function isTreatyReputation(payload: unknown): payload is TreatyReputation {
  return (
    isRecord(payload) &&
    isTreatyReputationSummary(payload.summary) &&
    Array.isArray(payload.history) &&
    payload.history.every(isTreatyHistoryRecord)
  );
}

function isTreatyReputationSummary(payload: unknown): payload is TreatyReputationSummary {
  return (
    isRecord(payload) &&
    typeof payload.signed === "number" &&
    typeof payload.active === "number" &&
    typeof payload.honored === "number" &&
    typeof payload.withdrawn === "number" &&
    typeof payload.broken_by_self === "number" &&
    typeof payload.broken_by_counterparty === "number"
  );
}

function isTreatyHistoryRecord(payload: unknown): payload is TreatyHistoryRecord {
  return (
    isRecord(payload) &&
    typeof payload.match_id === "string" &&
    typeof payload.counterparty_display_name === "string" &&
    typeof payload.treaty_type === "string" &&
    isTreatyHistoryStatus(payload.status) &&
    typeof payload.signed_tick === "number" &&
    (payload.ended_tick === null || typeof payload.ended_tick === "number") &&
    typeof payload.broken_by_self === "boolean"
  );
}

function isTreatyHistoryStatus(payload: unknown): payload is TreatyHistoryRecord["status"] {
  return (
    payload === "proposed" ||
    payload === "active" ||
    payload === "honored" ||
    payload === "broken_by_a" ||
    payload === "broken_by_b" ||
    payload === "withdrawn"
  );
}

function isLeaderboardEntry(payload: unknown): payload is LeaderboardEntry {
  if (!isRecord(payload)) {
    return false;
  }

  const hasValidSharedFields =
    typeof payload.rank === "number" &&
    typeof payload.display_name === "string" &&
    (payload.competitor_kind === "human" || payload.competitor_kind === "agent") &&
    typeof payload.elo === "number" &&
    typeof payload.provisional === "boolean" &&
    typeof payload.matches_played === "number" &&
    typeof payload.wins === "number" &&
    typeof payload.losses === "number" &&
    typeof payload.draws === "number";

  if (!hasValidSharedFields) {
    return false;
  }

  if (payload.competitor_kind === "human") {
    return payload.agent_id === null && typeof payload.human_id === "string";
  }

  return typeof payload.agent_id === "string" && payload.human_id === null;
}

function isAgentProfileRating(payload: unknown): payload is AgentProfileRating {
  return isRecord(payload) && typeof payload.elo === "number" && typeof payload.provisional === "boolean";
}

function isAgentProfileHistory(payload: unknown): payload is AgentProfileHistory {
  return (
    isRecord(payload) &&
    typeof payload.matches_played === "number" &&
    typeof payload.wins === "number" &&
    typeof payload.losses === "number" &&
    typeof payload.draws === "number"
  );
}
