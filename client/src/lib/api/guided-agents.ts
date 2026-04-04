import type {
  OwnedAgentGuidanceAcceptanceResponse,
  OwnedAgentGuidanceCreateRequest,
  OwnedAgentGuidedSessionResponse,
  OwnedAgentOverrideAcceptanceResponse,
  OwnedAgentOverrideCreateRequest
} from "../types";
import {
  buildAuthenticatedHeaders,
  buildAuthenticatedJsonHeaders,
  isApiErrorEnvelope,
  resolveApiBaseUrl
} from "./account-session";
import {
  GUIDED_AGENT_CONTROLS_ERROR_MESSAGE,
  isOwnedAgentGuidanceAcceptanceResponse,
  isOwnedAgentGuidedSessionResponse,
  isOwnedAgentOverrideAcceptanceResponse,
  type ResponseLike
} from "./authenticated-contracts";

export class GuidedAgentControlsError extends Error {
  constructor(
    message = GUIDED_AGENT_CONTROLS_ERROR_MESSAGE,
    readonly code: string = "guided_agent_controls_unavailable",
    readonly statusCode: number = 500
  ) {
    super(message);
    this.name = "GuidedAgentControlsError";
  }
}

export async function fetchOwnedAgentGuidedSession(
  matchId: string,
  agentId: string,
  bearerToken: string,
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<OwnedAgentGuidedSessionResponse> {
  const response = await fetchImpl(
    `${resolveApiBaseUrl(options?.apiBaseUrl)}/api/v1/matches/${encodeURIComponent(matchId)}/agents/${encodeURIComponent(agentId)}/guided-session`,
    {
      cache: "no-store",
      headers: buildAuthenticatedHeaders(bearerToken)
    }
  ).catch(() => {
    throw new GuidedAgentControlsError(
      GUIDED_AGENT_CONTROLS_ERROR_MESSAGE,
      "guided_agent_controls_unavailable",
      500
    );
  });

  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    throw toGuidedAgentControlsError(payload, response.status);
  }

  const payload: unknown = await response.json();
  if (!isOwnedAgentGuidedSessionResponse(payload)) {
    throw new GuidedAgentControlsError(
      GUIDED_AGENT_CONTROLS_ERROR_MESSAGE,
      "invalid_guided_session_response",
      response.status
    );
  }

  return payload;
}

export async function submitOwnedAgentGuidance(
  request: OwnedAgentGuidanceCreateRequest,
  agentId: string,
  bearerToken: string,
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<OwnedAgentGuidanceAcceptanceResponse> {
  const response = await fetchImpl(
    `${resolveApiBaseUrl(options?.apiBaseUrl)}/api/v1/matches/${encodeURIComponent(request.match_id)}/agents/${encodeURIComponent(agentId)}/guidance`,
    {
      method: "POST",
      cache: "no-store",
      headers: buildAuthenticatedJsonHeaders(bearerToken),
      body: JSON.stringify(request)
    }
  ).catch(() => {
    throw new GuidedAgentControlsError(
      GUIDED_AGENT_CONTROLS_ERROR_MESSAGE,
      "guided_agent_controls_unavailable",
      500
    );
  });

  return handleGuidedAgentControlsResponse(response, isOwnedAgentGuidanceAcceptanceResponse);
}

export async function submitOwnedAgentOverride(
  request: OwnedAgentOverrideCreateRequest,
  agentId: string,
  bearerToken: string,
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<OwnedAgentOverrideAcceptanceResponse> {
  const response = await fetchImpl(
    `${resolveApiBaseUrl(options?.apiBaseUrl)}/api/v1/matches/${encodeURIComponent(request.match_id)}/agents/${encodeURIComponent(agentId)}/override`,
    {
      method: "POST",
      cache: "no-store",
      headers: buildAuthenticatedJsonHeaders(bearerToken),
      body: JSON.stringify(request)
    }
  ).catch(() => {
    throw new GuidedAgentControlsError(
      GUIDED_AGENT_CONTROLS_ERROR_MESSAGE,
      "guided_agent_controls_unavailable",
      500
    );
  });

  return handleGuidedAgentControlsResponse(response, isOwnedAgentOverrideAcceptanceResponse);
}

async function handleGuidedAgentControlsResponse<T>(
  response: ResponseLike,
  validator: (payload: unknown) => payload is T
): Promise<T> {
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    throw toGuidedAgentControlsError(payload, response.status);
  }

  const payload: unknown = await response.json();
  if (!validator(payload)) {
    throw new GuidedAgentControlsError(
      GUIDED_AGENT_CONTROLS_ERROR_MESSAGE,
      "invalid_guided_response",
      response.status
    );
  }

  return payload;
}

function toGuidedAgentControlsError(payload: unknown, status: number): GuidedAgentControlsError {
  if (isApiErrorEnvelope(payload)) {
    return new GuidedAgentControlsError(payload.error.message, payload.error.code, status);
  }

  return new GuidedAgentControlsError(
    GUIDED_AGENT_CONTROLS_ERROR_MESSAGE,
    "guided_agent_controls_unavailable",
    status
  );
}
