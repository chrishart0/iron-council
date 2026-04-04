import type {
  MatchJoinRequest,
  MatchJoinResponse,
  MatchLobbyCreateRequest,
  MatchLobbyCreateResponse,
  MatchLobbyStartResponse
} from "../types";
import {
  buildAuthenticatedHeaders,
  buildAuthenticatedJsonHeaders,
  isApiErrorEnvelope,
  resolveApiBaseUrl
} from "./account-session";
import {
  isMatchJoinResponse,
  isMatchLobbyCreateResponse,
  isMatchSummary,
  MATCH_LOBBY_ERROR_MESSAGE,
  type ResponseLike
} from "./authenticated-contracts";

export class LobbyActionError extends Error {
  constructor(
    message = MATCH_LOBBY_ERROR_MESSAGE,
    readonly code: string = "lobby_action_unavailable",
    readonly statusCode: number = 500
  ) {
    super(message);
    this.name = "LobbyActionError";
  }
}

export async function createMatchLobby(
  request: MatchLobbyCreateRequest,
  bearerToken: string,
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<MatchLobbyCreateResponse> {
  const response = await fetchImpl(`${resolveApiBaseUrl(options?.apiBaseUrl)}/api/v1/matches`, {
    method: "POST",
    cache: "no-store",
    headers: buildAuthenticatedJsonHeaders(bearerToken),
    body: JSON.stringify(request)
  });

  return handleLobbyResponse(response, isMatchLobbyCreateResponse);
}

export async function joinMatchLobby(
  request: MatchJoinRequest,
  bearerToken: string,
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<MatchJoinResponse> {
  const response = await fetchImpl(
    `${resolveApiBaseUrl(options?.apiBaseUrl)}/api/v1/matches/${encodeURIComponent(request.match_id)}/join`,
    {
      method: "POST",
      cache: "no-store",
      headers: buildAuthenticatedJsonHeaders(bearerToken),
      body: JSON.stringify(request)
    }
  );

  return handleLobbyResponse(response, isMatchJoinResponse);
}

export async function startMatchLobby(
  matchId: string,
  bearerToken: string,
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<MatchLobbyStartResponse> {
  const response = await fetchImpl(
    `${resolveApiBaseUrl(options?.apiBaseUrl)}/api/v1/matches/${encodeURIComponent(matchId)}/start`,
    {
      method: "POST",
      cache: "no-store",
      headers: buildAuthenticatedHeaders(bearerToken)
    }
  );

  return handleLobbyResponse(response, isMatchSummary);
}

async function handleLobbyResponse<T>(
  response: ResponseLike,
  validator: (payload: unknown) => payload is T
): Promise<T> {
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    throw toLobbyActionError(payload, response.status);
  }

  const payload: unknown = await response.json();
  if (!validator(payload)) {
    throw new LobbyActionError(MATCH_LOBBY_ERROR_MESSAGE, "invalid_lobby_response", response.status);
  }

  return payload;
}

function toLobbyActionError(payload: unknown, status: number): LobbyActionError {
  if (isApiErrorEnvelope(payload)) {
    return new LobbyActionError(payload.error.message, payload.error.code, status);
  }

  return new LobbyActionError(MATCH_LOBBY_ERROR_MESSAGE, "lobby_action_unavailable", status);
}
