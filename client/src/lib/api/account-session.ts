import type {
  ApiErrorEnvelope,
  OwnedApiKeyCreateResponse,
  OwnedApiKeyListResponse,
  OwnedApiKeySummary
} from "../types";
import { DEFAULT_API_BASE_URL, normalizeApiBaseUrl } from "../session-storage";

const PUBLIC_MATCH_DETAIL_NOT_FOUND_MESSAGE =
  "This match is unavailable. It may not exist or may already be completed.";

const API_KEY_LIFECYCLE_ERROR_MESSAGE = "Unable to manage account API keys right now.";
const GUIDED_AGENT_CONTROLS_ERROR_MESSAGE = "Unable to load guided agent controls right now.";
const HUMAN_NOT_JOINED_MESSAGE =
  "Join this match as a human player before opening the authenticated live page.";
const INVALID_WEBSOCKET_AUTH_MESSAGE =
  "This live player page requires a valid human bearer token before it can connect.";
const PLAYER_AUTH_MISMATCH_MESSAGE = "This bearer token does not belong to the requested player.";

export class ApiKeyLifecycleError extends Error {
  constructor(
    message = API_KEY_LIFECYCLE_ERROR_MESSAGE,
    readonly code: string = "api_key_lifecycle_unavailable",
    readonly statusCode: number = 500
  ) {
    super(message);
    this.name = "ApiKeyLifecycleError";
  }
}

export async function fetchOwnedApiKeys(
  bearerToken: string,
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<OwnedApiKeyListResponse> {
  const response = await fetchImpl(`${resolveApiBaseUrl(options?.apiBaseUrl)}/api/v1/account/api-keys`, {
    cache: "no-store",
    headers: buildAuthenticatedHeaders(bearerToken)
  }).catch(() => {
    throw new ApiKeyLifecycleError(
      API_KEY_LIFECYCLE_ERROR_MESSAGE,
      "api_key_lifecycle_unavailable",
      500
    );
  });

  return handleApiKeyLifecycleResponse(response, isOwnedApiKeyListResponse);
}

export async function createOwnedApiKey(
  bearerToken: string,
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<OwnedApiKeyCreateResponse> {
  const response = await fetchImpl(`${resolveApiBaseUrl(options?.apiBaseUrl)}/api/v1/account/api-keys`, {
    method: "POST",
    cache: "no-store",
    headers: buildAuthenticatedHeaders(bearerToken)
  }).catch(() => {
    throw new ApiKeyLifecycleError(
      API_KEY_LIFECYCLE_ERROR_MESSAGE,
      "api_key_lifecycle_unavailable",
      500
    );
  });

  return handleApiKeyLifecycleResponse(response, isOwnedApiKeyCreateResponse);
}

export async function revokeOwnedApiKey(
  keyId: string,
  bearerToken: string,
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<OwnedApiKeySummary> {
  const response = await fetchImpl(
    `${resolveApiBaseUrl(options?.apiBaseUrl)}/api/v1/account/api-keys/${encodeURIComponent(keyId)}`,
    {
      method: "DELETE",
      cache: "no-store",
      headers: buildAuthenticatedHeaders(bearerToken)
    }
  ).catch(() => {
    throw new ApiKeyLifecycleError(
      API_KEY_LIFECYCLE_ERROR_MESSAGE,
      "api_key_lifecycle_unavailable",
      500
    );
  });

  return handleApiKeyLifecycleResponse(response, isOwnedApiKeySummary);
}

export function buildSpectatorMatchWebSocketUrl(
  matchId: string,
  options?: { apiBaseUrl?: string }
): string {
  const httpUrl = buildMatchWebSocketUrl(matchId, options);
  httpUrl.search = "viewer=spectator";
  return httpUrl.toString();
}

export function buildPlayerMatchWebSocketUrl(
  matchId: string,
  bearerToken: string,
  options?: { apiBaseUrl?: string }
): string {
  const httpUrl = buildMatchWebSocketUrl(matchId, options);
  httpUrl.searchParams.set("viewer", "player");
  httpUrl.searchParams.set("token", bearerToken);
  return httpUrl.toString();
}

export function getPlayerWebSocketCloseMessage(reason: string): string | null {
  switch (reason) {
    case "human_not_joined":
      return HUMAN_NOT_JOINED_MESSAGE;
    case "match_not_found":
      return PUBLIC_MATCH_DETAIL_NOT_FOUND_MESSAGE;
    case "invalid_websocket_auth":
      return INVALID_WEBSOCKET_AUTH_MESSAGE;
    case "player_auth_mismatch":
      return PLAYER_AUTH_MISMATCH_MESSAGE;
    default:
      return null;
  }
}

function buildMatchWebSocketUrl(matchId: string, options?: { apiBaseUrl?: string }): URL {
  const httpUrl = new URL(resolveApiBaseUrl(options?.apiBaseUrl));
  const basePath = httpUrl.pathname === "/" ? "" : httpUrl.pathname.replace(/\/$/, "");

  httpUrl.protocol = httpUrl.protocol === "https:" ? "wss:" : "ws:";
  httpUrl.pathname = `${basePath}/ws/match/${encodeURIComponent(matchId)}`;
  httpUrl.search = "";
  return httpUrl;
}

export function buildAuthenticatedHeaders(bearerToken: string): HeadersInit {
  return {
    accept: "application/json",
    authorization: `Bearer ${bearerToken}`
  };
}

export function buildAuthenticatedJsonHeaders(bearerToken: string): HeadersInit {
  return {
    ...buildAuthenticatedHeaders(bearerToken),
    "content-type": "application/json"
  };
}

async function handleApiKeyLifecycleResponse<T>(
  response: ResponseLike,
  validator: (payload: unknown) => payload is T
): Promise<T> {
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    throw toApiKeyLifecycleError(payload, response.status);
  }

  const payload: unknown = await response.json().catch(() => {
    throw new ApiKeyLifecycleError(
      API_KEY_LIFECYCLE_ERROR_MESSAGE,
      "invalid_api_key_lifecycle_response",
      response.status
    );
  });
  if (!validator(payload)) {
    throw new ApiKeyLifecycleError(
      API_KEY_LIFECYCLE_ERROR_MESSAGE,
      "invalid_api_key_lifecycle_response",
      response.status
    );
  }

  return payload;
}

type ResponseLike = {
  ok: boolean;
  status: number;
  json(): Promise<unknown>;
};

function toApiKeyLifecycleError(payload: unknown, status: number): ApiKeyLifecycleError {
  if (isApiErrorEnvelope(payload)) {
    return new ApiKeyLifecycleError(payload.error.message, payload.error.code, status);
  }

  return new ApiKeyLifecycleError(
    API_KEY_LIFECYCLE_ERROR_MESSAGE,
    "api_key_lifecycle_unavailable",
    status
  );
}

export function isApiErrorEnvelope(payload: unknown): payload is ApiErrorEnvelope {
  return (
    isRecord(payload) &&
    isRecord(payload.error) &&
    typeof payload.error.code === "string" &&
    typeof payload.error.message === "string"
  );
}

function isOwnedApiKeyListResponse(payload: unknown): payload is OwnedApiKeyListResponse {
  return isRecord(payload) && Array.isArray(payload.items) && payload.items.every(isOwnedApiKeySummary);
}

function isOwnedApiKeyCreateResponse(payload: unknown): payload is OwnedApiKeyCreateResponse {
  return (
    isRecord(payload) &&
    typeof payload.api_key === "string" &&
    isOwnedApiKeySummary(payload.summary)
  );
}

function isOwnedApiKeySummary(payload: unknown): payload is OwnedApiKeySummary {
  return (
    isRecord(payload) &&
    typeof payload.key_id === "string" &&
    typeof payload.agent_id === "string" &&
    typeof payload.elo_rating === "number" &&
    typeof payload.is_active === "boolean" &&
    typeof payload.created_at === "string" &&
    isApiKeyEntitlementSummary(payload.entitlement)
  );
}

function isApiKeyEntitlementSummary(payload: unknown): boolean {
  return (
    isRecord(payload) &&
    typeof payload.is_entitled === "boolean" &&
    (payload.grant_source === "manual" ||
      payload.grant_source === "dev" ||
      payload.grant_source === null ||
      payload.grant_source === undefined) &&
    typeof payload.concurrent_match_allowance === "number" &&
    (typeof payload.granted_at === "string" || payload.granted_at === null || payload.granted_at === undefined)
  );
}

export function resolveApiBaseUrl(explicitBaseUrl?: string): string {
  if (explicitBaseUrl) {
    return normalizeApiBaseUrl(explicitBaseUrl);
  }

  return DEFAULT_API_BASE_URL;
}

export function isRecord(payload: unknown): payload is Record<string, unknown> {
  return typeof payload === "object" && payload !== null;
}
