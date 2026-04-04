import type {
  AgentProfileHistory,
  AgentProfileRating,
  AllianceMemberRecord,
  AllianceRecord,
  ApiErrorEnvelope,
  BuildingQueueItem,
  CityUpgradeState,
  CompletedMatchSummary,
  CompletedMatchSummaryListResponse,
  DirectMessageRecord,
  GroupChatRecord,
  GroupMessageRecord,
  LeaderboardEntry,
  MatchHistoryEntry,
  MatchListResponse,
  MatchReplayTickResponse,
  MatchSummary,
  PlayerMatchEnvelope,
  PlayerMatchState,
  PublicAgentProfileResponse,
  PublicHumanProfileResponse,
  PublicLeaderboardResponse,
  PublicMatchDetailResponse,
  PublicMatchHistoryResponse,
  PublicMatchRosterRow,
  ReplayFieldRecord,
  ReplayFieldValue,
  ResourceState,
  SpectatorArmyState,
  SpectatorCityState,
  SpectatorMatchEnvelope,
  SpectatorMatchState,
  SpectatorPlayerState,
  TreatyHistoryRecord,
  TreatyRecord,
  TreatyReputation,
  TreatyReputationSummary,
  UnknownField,
  VictoryState,
  VisibleArmyState,
  VisibleCityState,
  WorldMessageRecord
} from "../types";
import { DEFAULT_API_BASE_URL, normalizeApiBaseUrl } from "../session-storage";

const PUBLIC_MATCHES_ERROR_MESSAGE = "Unable to load public matches right now.";
const PUBLIC_MATCH_DETAIL_ERROR_MESSAGE = "Unable to load this public match right now.";
const PUBLIC_LEADERBOARD_ERROR_MESSAGE = "Unable to load the public leaderboard right now.";
const PUBLIC_AGENT_PROFILE_ERROR_MESSAGE = "Unable to load this agent profile right now.";
const PUBLIC_HUMAN_PROFILE_ERROR_MESSAGE = "Unable to load this human profile right now.";
const COMPLETED_MATCHES_ERROR_MESSAGE = "Unable to load completed matches right now.";
const PUBLIC_MATCH_DETAIL_NOT_FOUND_MESSAGE =
  "This match is unavailable. It may not exist or may already be completed.";
const PUBLIC_MATCH_HISTORY_ERROR_MESSAGE = "Unable to load match history right now.";
const PUBLIC_MATCH_HISTORY_NOT_FOUND_MESSAGE =
  "This completed match history is unavailable. It may not exist.";
const PUBLIC_AGENT_PROFILE_NOT_FOUND_MESSAGE =
  "This agent profile is unavailable. It may not exist.";
const PUBLIC_HUMAN_PROFILE_NOT_FOUND_MESSAGE =
  "This human profile is unavailable. It may not exist.";
const MATCH_REPLAY_TICK_ERROR_MESSAGE = "Unable to load this replay tick right now.";
const MATCH_REPLAY_TICK_NOT_FOUND_MESSAGE =
  "This replay tick is unavailable for the selected match.";
const PLAYER_MATCH_UPDATE_ERROR_MESSAGE = "Unable to parse player live match update.";
const SPECTATOR_MATCH_UPDATE_ERROR_MESSAGE = "Unable to parse spectator live match update.";

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

export class CompletedMatchesError extends Error {
  constructor(message = COMPLETED_MATCHES_ERROR_MESSAGE) {
    super(message);
    this.name = "CompletedMatchesError";
  }
}

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

export async function fetchPublicLeaderboard(
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<PublicLeaderboardResponse> {
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
}

export async function fetchPublicAgentProfile(
  agentId: string,
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<PublicAgentProfileResponse> {
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
}

export async function fetchPublicHumanProfile(
  humanId: string,
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<PublicHumanProfileResponse> {
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
}

export async function fetchCompletedMatches(
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<CompletedMatchSummaryListResponse> {
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
}

export async function fetchPublicMatchHistory(
  matchId: string,
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<PublicMatchHistoryResponse> {
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
}

export async function fetchMatchReplayTick(
  matchId: string,
  tick: number,
  fetchImpl: typeof fetch = fetch,
  options?: { apiBaseUrl?: string }
): Promise<MatchReplayTickResponse> {
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

function isCompletedMatchSummaryListResponse(
  payload: unknown
): payload is CompletedMatchSummaryListResponse {
  if (!isRecord(payload) || !Array.isArray(payload.matches)) {
    return false;
  }

  return payload.matches.every(isCompletedMatchSummary);
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

function hasApiErrorCode(payload: unknown, code: string): boolean {
  return isApiErrorEnvelope(payload) && payload.error.code === code;
}

function isApiErrorEnvelope(payload: unknown): payload is ApiErrorEnvelope {
  return (
    isRecord(payload) &&
    isRecord(payload.error) &&
    typeof payload.error.code === "string" &&
    typeof payload.error.message === "string"
  );
}

function isRecord(payload: unknown): payload is Record<string, unknown> {
  return typeof payload === "object" && payload !== null;
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
