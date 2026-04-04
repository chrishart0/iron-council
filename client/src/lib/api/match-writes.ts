import type {
  AllianceActionAcceptanceResponse,
  AllianceActionRequest,
  GroupChatCreateAcceptanceResponse,
  GroupChatCreateRequest,
  GroupChatMessageAcceptanceResponse,
  GroupChatMessageCreateRequest,
  MatchMessageCreateRequest,
  MatchOrdersCommandRequest,
  MessageAcceptanceResponse,
  OrderAcceptanceResponse,
  TreatyActionAcceptanceResponse,
  TreatyActionRequest
} from "../types";
import {
  buildAuthenticatedJsonHeaders,
  isApiErrorEnvelope,
  resolveApiBaseUrl
} from "./account-session";
import {
  COMMAND_SUBMISSION_ERROR_MESSAGE,
  DIPLOMACY_SUBMISSION_ERROR_MESSAGE,
  GROUP_CHAT_CREATE_ERROR_MESSAGE,
  isAllianceActionAcceptanceResponse,
  isGroupChatCreateAcceptanceResponse,
  isGroupChatMessageAcceptanceResponse,
  isMatchOrdersCommandEnvelopeResponse,
  isMessageAcceptanceResponse,
  isTreatyActionAcceptanceResponse,
  MESSAGE_SUBMISSION_ERROR_MESSAGE,
  type ResponseLike
} from "./authenticated-contracts";

export class CommandSubmissionError extends Error {
  constructor(
    message = COMMAND_SUBMISSION_ERROR_MESSAGE,
    readonly code: string = "command_submission_unavailable",
    readonly statusCode: number = 500
  ) {
    super(message);
    this.name = "CommandSubmissionError";
  }
}

export class MessageSubmissionError extends Error {
  constructor(
    message = MESSAGE_SUBMISSION_ERROR_MESSAGE,
    readonly code: string = "message_submission_unavailable",
    readonly statusCode: number = 500
  ) {
    super(message);
    this.name = "MessageSubmissionError";
  }
}

export class GroupChatCreateError extends Error {
  constructor(
    message = GROUP_CHAT_CREATE_ERROR_MESSAGE,
    readonly code: string = "group_chat_create_unavailable",
    readonly statusCode: number = 500
  ) {
    super(message);
    this.name = "GroupChatCreateError";
  }
}

export class DiplomacySubmissionError extends Error {
  constructor(
    message = DIPLOMACY_SUBMISSION_ERROR_MESSAGE,
    readonly code: string = "diplomacy_submission_unavailable",
    readonly statusCode: number = 500
  ) {
    super(message);
    this.name = "DiplomacySubmissionError";
  }
}

export async function submitMatchOrders(
  request: MatchOrdersCommandRequest,
  bearerToken: string,
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<OrderAcceptanceResponse> {
  const response = await fetchImpl(
    `${resolveApiBaseUrl(options?.apiBaseUrl)}/api/v1/matches/${encodeURIComponent(request.match_id)}/commands`,
    {
      method: "POST",
      cache: "no-store",
      headers: buildAuthenticatedJsonHeaders(bearerToken),
      body: JSON.stringify({
        ...request,
        messages: [],
        treaties: [],
        alliance: null
      })
    }
  ).catch(() => {
    throw new CommandSubmissionError(
      COMMAND_SUBMISSION_ERROR_MESSAGE,
      "command_submission_unavailable",
      500
    );
  });

  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    throw toCommandSubmissionError(payload, response.status);
  }

  const payload: unknown = await response.json();
  if (!isMatchOrdersCommandEnvelopeResponse(payload) || payload.orders === null) {
    throw new CommandSubmissionError(
      COMMAND_SUBMISSION_ERROR_MESSAGE,
      "invalid_command_response",
      response.status
    );
  }

  return payload.orders;
}

export async function submitMatchMessage(
  request: MatchMessageCreateRequest,
  bearerToken: string,
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<MessageAcceptanceResponse> {
  const response = await fetchImpl(
    `${resolveApiBaseUrl(options?.apiBaseUrl)}/api/v1/matches/${encodeURIComponent(request.match_id)}/messages`,
    {
      method: "POST",
      cache: "no-store",
      headers: buildAuthenticatedJsonHeaders(bearerToken),
      body: JSON.stringify(request)
    }
  ).catch(() => {
    throw new MessageSubmissionError(
      MESSAGE_SUBMISSION_ERROR_MESSAGE,
      "message_submission_unavailable",
      500
    );
  });

  return handleMessageSubmissionResponse(response, isMessageAcceptanceResponse);
}

export async function submitGroupChatMessage(
  groupChatId: string,
  request: GroupChatMessageCreateRequest,
  bearerToken: string,
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<GroupChatMessageAcceptanceResponse> {
  const response = await fetchImpl(
    `${resolveApiBaseUrl(options?.apiBaseUrl)}/api/v1/matches/${encodeURIComponent(request.match_id)}/group-chats/${encodeURIComponent(groupChatId)}/messages`,
    {
      method: "POST",
      cache: "no-store",
      headers: buildAuthenticatedJsonHeaders(bearerToken),
      body: JSON.stringify(request)
    }
  ).catch(() => {
    throw new MessageSubmissionError(
      MESSAGE_SUBMISSION_ERROR_MESSAGE,
      "message_submission_unavailable",
      500
    );
  });

  return handleMessageSubmissionResponse(response, isGroupChatMessageAcceptanceResponse);
}

export async function submitGroupChatCreate(
  request: GroupChatCreateRequest,
  bearerToken: string,
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<GroupChatCreateAcceptanceResponse> {
  const response = await fetchImpl(
    `${resolveApiBaseUrl(options?.apiBaseUrl)}/api/v1/matches/${encodeURIComponent(request.match_id)}/group-chats`,
    {
      method: "POST",
      cache: "no-store",
      headers: buildAuthenticatedJsonHeaders(bearerToken),
      body: JSON.stringify(request)
    }
  ).catch(() => {
    throw new GroupChatCreateError(
      GROUP_CHAT_CREATE_ERROR_MESSAGE,
      "group_chat_create_unavailable",
      500
    );
  });

  return handleGroupChatCreateResponse(response, isGroupChatCreateAcceptanceResponse);
}

export async function submitTreatyAction(
  request: TreatyActionRequest,
  bearerToken: string,
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<TreatyActionAcceptanceResponse> {
  const response = await fetchImpl(
    `${resolveApiBaseUrl(options?.apiBaseUrl)}/api/v1/matches/${encodeURIComponent(request.match_id)}/treaties`,
    {
      method: "POST",
      cache: "no-store",
      headers: buildAuthenticatedJsonHeaders(bearerToken),
      body: JSON.stringify(request)
    }
  ).catch(() => {
    throw new DiplomacySubmissionError(
      DIPLOMACY_SUBMISSION_ERROR_MESSAGE,
      "diplomacy_submission_unavailable",
      500
    );
  });

  return handleDiplomacySubmissionResponse(response, isTreatyActionAcceptanceResponse);
}

export async function submitAllianceAction(
  request: AllianceActionRequest,
  bearerToken: string,
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<AllianceActionAcceptanceResponse> {
  const response = await fetchImpl(
    `${resolveApiBaseUrl(options?.apiBaseUrl)}/api/v1/matches/${encodeURIComponent(request.match_id)}/alliances`,
    {
      method: "POST",
      cache: "no-store",
      headers: buildAuthenticatedJsonHeaders(bearerToken),
      body: JSON.stringify(request)
    }
  ).catch(() => {
    throw new DiplomacySubmissionError(
      DIPLOMACY_SUBMISSION_ERROR_MESSAGE,
      "diplomacy_submission_unavailable",
      500
    );
  });

  return handleDiplomacySubmissionResponse(response, isAllianceActionAcceptanceResponse);
}

async function handleMessageSubmissionResponse<T>(
  response: ResponseLike,
  validator: (payload: unknown) => payload is T
): Promise<T> {
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    throw toMessageSubmissionError(payload, response.status);
  }

  const payload: unknown = await response.json();
  if (!validator(payload)) {
    throw new MessageSubmissionError(
      MESSAGE_SUBMISSION_ERROR_MESSAGE,
      "invalid_message_response",
      response.status
    );
  }

  return payload;
}

async function handleGroupChatCreateResponse<T>(
  response: ResponseLike,
  validator: (payload: unknown) => payload is T
): Promise<T> {
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    throw toGroupChatCreateError(payload, response.status);
  }

  const payload: unknown = await response.json();
  if (!validator(payload)) {
    throw new GroupChatCreateError(
      GROUP_CHAT_CREATE_ERROR_MESSAGE,
      "invalid_group_chat_create_response",
      response.status
    );
  }

  return payload;
}

async function handleDiplomacySubmissionResponse<T>(
  response: ResponseLike,
  validator: (payload: unknown) => payload is T
): Promise<T> {
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    throw toDiplomacySubmissionError(payload, response.status);
  }

  const payload: unknown = await response.json();
  if (!validator(payload)) {
    throw new DiplomacySubmissionError(
      DIPLOMACY_SUBMISSION_ERROR_MESSAGE,
      "invalid_diplomacy_response",
      response.status
    );
  }

  return payload;
}

function toCommandSubmissionError(payload: unknown, status: number): CommandSubmissionError {
  if (isApiErrorEnvelope(payload)) {
    return new CommandSubmissionError(payload.error.message, payload.error.code, status);
  }

  return new CommandSubmissionError(
    COMMAND_SUBMISSION_ERROR_MESSAGE,
    "command_submission_unavailable",
    status
  );
}

function toMessageSubmissionError(payload: unknown, status: number): MessageSubmissionError {
  if (isApiErrorEnvelope(payload)) {
    return new MessageSubmissionError(payload.error.message, payload.error.code, status);
  }

  return new MessageSubmissionError(
    MESSAGE_SUBMISSION_ERROR_MESSAGE,
    "message_submission_unavailable",
    status
  );
}

function toGroupChatCreateError(payload: unknown, status: number): GroupChatCreateError {
  if (isApiErrorEnvelope(payload)) {
    return new GroupChatCreateError(payload.error.message, payload.error.code, status);
  }

  return new GroupChatCreateError(
    GROUP_CHAT_CREATE_ERROR_MESSAGE,
    "group_chat_create_unavailable",
    status
  );
}

function toDiplomacySubmissionError(payload: unknown, status: number): DiplomacySubmissionError {
  if (isApiErrorEnvelope(payload)) {
    return new DiplomacySubmissionError(payload.error.message, payload.error.code, status);
  }

  return new DiplomacySubmissionError(
    DIPLOMACY_SUBMISSION_ERROR_MESSAGE,
    "diplomacy_submission_unavailable",
    status
  );
}
