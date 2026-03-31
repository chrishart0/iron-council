import type {
  AllianceRecord,
  AllianceMemberRecord,
  ApiErrorEnvelope,
  BuildingQueueItem,
  CityUpgradeState,
  DirectMessageRecord,
  GroupChatRecord,
  GroupMessageRecord,
  MatchOrdersCommandEnvelopeResponse,
  MatchOrdersCommandRequest,
  MatchJoinRequest,
  MatchJoinResponse,
  MatchListResponse,
  MatchLobbyCreateRequest,
  MatchLobbyCreateResponse,
  MatchLobbyStartResponse,
  MatchSummary,
  OrderAcceptanceResponse,
  PlayerMatchEnvelope,
  PlayerMatchState,
  PublicMatchDetailResponse,
  PublicMatchRosterRow,
  ResourceState,
  UnknownField,
  VisibleArmyState,
  VisibleCityState,
  SpectatorArmyState,
  SpectatorCityState,
  SpectatorMatchEnvelope,
  SpectatorMatchState,
  SpectatorPlayerState,
  TreatyRecord,
  VictoryState,
  WorldMessageRecord
} from "./types";
import { DEFAULT_API_BASE_URL, normalizeApiBaseUrl } from "./session-storage";

const PUBLIC_MATCHES_ERROR_MESSAGE = "Unable to load public matches right now.";
const PUBLIC_MATCH_DETAIL_ERROR_MESSAGE = "Unable to load this public match right now.";
const PUBLIC_MATCH_DETAIL_NOT_FOUND_MESSAGE =
  "This match is unavailable. It may not exist or may already be completed.";
const PLAYER_MATCH_UPDATE_ERROR_MESSAGE = "Unable to parse player live match update.";
const SPECTATOR_MATCH_UPDATE_ERROR_MESSAGE = "Unable to parse spectator live match update.";
const MATCH_LOBBY_ERROR_MESSAGE = "Unable to complete the requested lobby action right now.";
const COMMAND_SUBMISSION_ERROR_MESSAGE = "Unable to submit orders right now.";
const HUMAN_NOT_JOINED_MESSAGE =
  "Join this match as a human player before opening the authenticated live page.";
const INVALID_WEBSOCKET_AUTH_MESSAGE =
  "This live player page requires a valid human bearer token before it can connect.";
const PLAYER_AUTH_MISMATCH_MESSAGE = "This bearer token does not belong to the requested player.";

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

export function parsePlayerMatchEnvelope(payload: unknown): PlayerMatchEnvelope {
  if (!isPlayerMatchEnvelope(payload)) {
    throw new Error(PLAYER_MATCH_UPDATE_ERROR_MESSAGE);
  }

  return payload;
}

export function parseSpectatorMatchEnvelope(payload: unknown): SpectatorMatchEnvelope {
  if (!isSpectatorMatchEnvelope(payload)) {
    throw new Error(SPECTATOR_MATCH_UPDATE_ERROR_MESSAGE);
  }

  return payload;
}

export function parseWebSocketApiErrorEnvelope(payload: unknown): ApiErrorEnvelope | null {
  return isApiErrorEnvelope(payload) ? payload : null;
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

function buildAuthenticatedHeaders(bearerToken: string): HeadersInit {
  return {
    accept: "application/json",
    authorization: `Bearer ${bearerToken}`
  };
}

function buildAuthenticatedJsonHeaders(bearerToken: string): HeadersInit {
  return {
    ...buildAuthenticatedHeaders(bearerToken),
    "content-type": "application/json"
  };
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

type ResponseLike = {
  ok: boolean;
  status: number;
  json(): Promise<unknown>;
};

function toLobbyActionError(payload: unknown, status: number): LobbyActionError {
  if (isApiErrorEnvelope(payload)) {
    return new LobbyActionError(payload.error.message, payload.error.code, status);
  }
  return new LobbyActionError(MATCH_LOBBY_ERROR_MESSAGE, "lobby_action_unavailable", status);
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

function isApiErrorEnvelope(payload: unknown): payload is ApiErrorEnvelope {
  return (
    isRecord(payload) &&
    isRecord(payload.error) &&
    typeof payload.error.code === "string" &&
    typeof payload.error.message === "string"
  );
}

function isMatchLobbyCreateResponse(payload: unknown): payload is MatchLobbyCreateResponse {
  return isMatchSummary(payload) && typeof (payload as Record<string, unknown>).creator_player_id === "string";
}

function isMatchJoinResponse(payload: unknown): payload is MatchJoinResponse {
  return (
    isRecord(payload) &&
    payload.status === "accepted" &&
    typeof payload.match_id === "string" &&
    typeof payload.agent_id === "string" &&
    typeof payload.player_id === "string"
  );
}

function isMatchOrdersCommandEnvelopeResponse(
  payload: unknown
): payload is MatchOrdersCommandEnvelopeResponse {
  return (
    isRecord(payload) &&
    payload.status === "accepted" &&
    typeof payload.match_id === "string" &&
    typeof payload.player_id === "string" &&
    typeof payload.tick === "number" &&
    (payload.orders === null || isOrderAcceptanceResponse(payload.orders)) &&
    Array.isArray(payload.messages) &&
    Array.isArray(payload.treaties) &&
    (payload.alliance === null || isRecord(payload.alliance))
  );
}

function isOrderAcceptanceResponse(payload: unknown): payload is OrderAcceptanceResponse {
  return (
    isRecord(payload) &&
    payload.status === "accepted" &&
    typeof payload.match_id === "string" &&
    typeof payload.player_id === "string" &&
    typeof payload.tick === "number" &&
    typeof payload.submission_index === "number"
  );
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

function isSpectatorMatchEnvelope(payload: unknown): payload is SpectatorMatchEnvelope {
  if (!isRecord(payload) || payload.type !== "tick_update" || !isRecord(payload.data)) {
    return false;
  }

  return (
    typeof payload.data.match_id === "string" &&
    payload.data.viewer_role === "spectator" &&
    payload.data.player_id === null &&
    isSpectatorMatchState(payload.data.state) &&
    Array.isArray(payload.data.world_messages) &&
    payload.data.world_messages.every(isWorldMessageRecord) &&
    Array.isArray(payload.data.direct_messages) &&
    payload.data.direct_messages.every(isDirectMessageRecord) &&
    Array.isArray(payload.data.group_chats) &&
    payload.data.group_chats.every(isGroupChatRecord) &&
    Array.isArray(payload.data.group_messages) &&
    payload.data.group_messages.every(isGroupMessageRecord) &&
    Array.isArray(payload.data.treaties) &&
    payload.data.treaties.every(isTreatyRecord) &&
    Array.isArray(payload.data.alliances) &&
    payload.data.alliances.every(isAllianceRecord)
  );
}

function isPlayerMatchEnvelope(payload: unknown): payload is PlayerMatchEnvelope {
  if (!isRecord(payload) || payload.type !== "tick_update" || !isRecord(payload.data)) {
    return false;
  }

  return (
    typeof payload.data.match_id === "string" &&
    payload.data.viewer_role === "player" &&
    typeof payload.data.player_id === "string" &&
    isPlayerMatchState(payload.data.state) &&
    payload.data.player_id === payload.data.state.player_id &&
    Array.isArray(payload.data.world_messages) &&
    payload.data.world_messages.every(isWorldMessageRecord) &&
    Array.isArray(payload.data.direct_messages) &&
    payload.data.direct_messages.every(isDirectMessageRecord) &&
    Array.isArray(payload.data.group_chats) &&
    payload.data.group_chats.every(isGroupChatRecord) &&
    Array.isArray(payload.data.group_messages) &&
    payload.data.group_messages.every(isGroupMessageRecord) &&
    Array.isArray(payload.data.treaties) &&
    payload.data.treaties.every(isTreatyRecord) &&
    Array.isArray(payload.data.alliances) &&
    payload.data.alliances.every(isAllianceRecord)
  );
}

function isPlayerMatchState(payload: unknown): payload is PlayerMatchState {
  if (!isRecord(payload)) {
    return false;
  }

  return (
    typeof payload.match_id === "string" &&
    typeof payload.tick === "number" &&
    typeof payload.player_id === "string" &&
    isResourceState(payload.resources) &&
    isRecord(payload.cities) &&
    Object.values(payload.cities).every(isVisibleCityState) &&
    Array.isArray(payload.visible_armies) &&
    payload.visible_armies.every(isVisibleArmyState) &&
    (typeof payload.alliance_id === "string" || payload.alliance_id === null) &&
    Array.isArray(payload.alliance_members) &&
    payload.alliance_members.every((memberId) => typeof memberId === "string") &&
    isVictoryState(payload.victory)
  );
}

function isSpectatorMatchState(payload: unknown): payload is SpectatorMatchState {
  if (!isRecord(payload)) {
    return false;
  }

  return (
    typeof payload.match_id === "string" &&
    typeof payload.tick === "number" &&
    isRecord(payload.cities) &&
    Object.values(payload.cities).every(isSpectatorCityState) &&
    Array.isArray(payload.armies) &&
    payload.armies.every(isSpectatorArmyState) &&
    isRecord(payload.players) &&
    Object.values(payload.players).every(isSpectatorPlayerState) &&
    isVictoryState(payload.victory)
  );
}

function isSpectatorCityState(payload: unknown): payload is SpectatorCityState {
  if (!isRecord(payload)) {
    return false;
  }

  return (
    (typeof payload.owner === "string" || payload.owner === null) &&
    typeof payload.population === "number" &&
    isResourceState(payload.resources) &&
    isCityUpgradeState(payload.upgrades) &&
    typeof payload.garrison === "number" &&
    Array.isArray(payload.building_queue) &&
    payload.building_queue.every(isBuildingQueueItem)
  );
}

function isUnknownField(payload: unknown): payload is UnknownField {
  return payload === "unknown";
}

function isVisibleCityState(payload: unknown): payload is VisibleCityState {
  if (!isRecord(payload)) {
    return false;
  }

  return (
    (typeof payload.owner === "string" || payload.owner === null) &&
    isFogVisibility(payload.visibility) &&
    (typeof payload.population === "number" || isUnknownField(payload.population)) &&
    (isResourceState(payload.resources) || isUnknownField(payload.resources)) &&
    (isCityUpgradeState(payload.upgrades) || isUnknownField(payload.upgrades)) &&
    (typeof payload.garrison === "number" || isUnknownField(payload.garrison)) &&
    ((Array.isArray(payload.building_queue) && payload.building_queue.every(isBuildingQueueItem)) ||
      isUnknownField(payload.building_queue))
  );
}

function isResourceState(payload: unknown): payload is ResourceState {
  return (
    isRecord(payload) &&
    typeof payload.food === "number" &&
    typeof payload.production === "number" &&
    typeof payload.money === "number"
  );
}

function isFogVisibility(payload: unknown): payload is "full" | "partial" {
  return payload === "full" || payload === "partial";
}

function isCityUpgradeState(payload: unknown): payload is CityUpgradeState {
  return (
    isRecord(payload) &&
    typeof payload.economy === "number" &&
    typeof payload.military === "number" &&
    typeof payload.fortification === "number"
  );
}

function isBuildingQueueItem(payload: unknown): payload is BuildingQueueItem {
  return (
    isRecord(payload) &&
    typeof payload.type === "string" &&
    typeof payload.tier === "number" &&
    typeof payload.ticks_remaining === "number"
  );
}

function isVisibleArmyState(payload: unknown): payload is VisibleArmyState {
  if (!isRecord(payload)) {
    return false;
  }

  const path = payload.path;

  return (
    typeof payload.id === "string" &&
    typeof payload.owner === "string" &&
    isFogVisibility(payload.visibility) &&
    (typeof payload.troops === "number" || isUnknownField(payload.troops)) &&
    (typeof payload.location === "string" || payload.location === null) &&
    (typeof payload.destination === "string" || payload.destination === null) &&
    (path === null ||
      isUnknownField(path) ||
      (Array.isArray(path) && path.every((segment) => typeof segment === "string"))) &&
    typeof payload.ticks_remaining === "number"
  );
}

function isSpectatorArmyState(payload: unknown): payload is SpectatorArmyState {
  if (!isRecord(payload)) {
    return false;
  }

  const path = payload.path;

  return (
    typeof payload.id === "string" &&
    typeof payload.owner === "string" &&
    typeof payload.troops === "number" &&
    (typeof payload.location === "string" || payload.location === null) &&
    (typeof payload.destination === "string" || payload.destination === null) &&
    (path === null || (Array.isArray(path) && path.every((segment) => typeof segment === "string"))) &&
    typeof payload.ticks_remaining === "number"
  );
}

function isSpectatorPlayerState(payload: unknown): payload is SpectatorPlayerState {
  return (
    isRecord(payload) &&
    isResourceState(payload.resources) &&
    Array.isArray(payload.cities_owned) &&
    payload.cities_owned.every((city) => typeof city === "string") &&
    (typeof payload.alliance_id === "string" || payload.alliance_id === null) &&
    typeof payload.is_eliminated === "boolean"
  );
}

function isVictoryState(payload: unknown): payload is VictoryState {
  return (
    isRecord(payload) &&
    (typeof payload.leading_alliance === "string" || payload.leading_alliance === null) &&
    typeof payload.cities_held === "number" &&
    typeof payload.threshold === "number" &&
    (typeof payload.countdown_ticks_remaining === "number" ||
      payload.countdown_ticks_remaining === null)
  );
}

function isWorldMessageRecord(payload: unknown): payload is WorldMessageRecord {
  return isMessageRecord(payload) && payload.channel === "world" && payload.recipient_id === null;
}

function isDirectMessageRecord(payload: unknown): payload is DirectMessageRecord {
  return (
    isMessageRecord(payload) &&
    payload.channel === "direct" &&
    (typeof payload.recipient_id === "string" || payload.recipient_id === null)
  );
}

function isMessageRecord(payload: unknown): payload is WorldMessageRecord | DirectMessageRecord {
  return (
    isRecord(payload) &&
    typeof payload.message_id === "number" &&
    typeof payload.sender_id === "string" &&
    typeof payload.tick === "number" &&
    typeof payload.content === "string" &&
    (payload.channel === "world" || payload.channel === "direct")
  );
}

function isGroupChatRecord(payload: unknown): payload is GroupChatRecord {
  return (
    isRecord(payload) &&
    typeof payload.group_chat_id === "string" &&
    typeof payload.name === "string" &&
    Array.isArray(payload.member_ids) &&
    payload.member_ids.every((memberId) => typeof memberId === "string") &&
    typeof payload.created_by === "string" &&
    typeof payload.created_tick === "number"
  );
}

function isGroupMessageRecord(payload: unknown): payload is GroupMessageRecord {
  return (
    isRecord(payload) &&
    typeof payload.message_id === "number" &&
    typeof payload.group_chat_id === "string" &&
    typeof payload.sender_id === "string" &&
    typeof payload.tick === "number" &&
    typeof payload.content === "string"
  );
}

function isTreatyRecord(payload: unknown): payload is TreatyRecord {
  return (
    isRecord(payload) &&
    typeof payload.treaty_id === "number" &&
    typeof payload.player_a_id === "string" &&
    typeof payload.player_b_id === "string" &&
    typeof payload.treaty_type === "string" &&
    typeof payload.status === "string" &&
    typeof payload.proposed_by === "string" &&
    typeof payload.proposed_tick === "number" &&
    (typeof payload.signed_tick === "number" || payload.signed_tick === null) &&
    (typeof payload.withdrawn_by === "string" || payload.withdrawn_by === null) &&
    (typeof payload.withdrawn_tick === "number" || payload.withdrawn_tick === null)
  );
}

function isAllianceRecord(payload: unknown): payload is AllianceRecord {
  return (
    isRecord(payload) &&
    typeof payload.alliance_id === "string" &&
    typeof payload.name === "string" &&
    typeof payload.leader_id === "string" &&
    typeof payload.formed_tick === "number" &&
    Array.isArray(payload.members) &&
    payload.members.every(isAllianceMemberRecord)
  );
}

function isAllianceMemberRecord(payload: unknown): payload is AllianceMemberRecord {
  return (
    isRecord(payload) &&
    typeof payload.player_id === "string" &&
    typeof payload.joined_tick === "number"
  );
}
