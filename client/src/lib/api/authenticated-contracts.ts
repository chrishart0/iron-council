import type {
  AllianceActionAcceptanceResponse,
  AllianceMemberRecord,
  AllianceRecord,
  BuildingQueueItem,
  CityUpgradeState,
  DirectMessageRecord,
  GroupChatCreateAcceptanceResponse,
  GroupChatMessageAcceptanceResponse,
  GroupChatRecord,
  GroupMessageRecord,
  GuidedSessionGuidanceRecord,
  MatchJoinResponse,
  MatchLobbyCreateResponse,
  MatchOrdersCommandEnvelopeResponse,
  MatchSummary,
  MessageAcceptanceResponse,
  OrderAcceptanceResponse,
  OwnedAgentGuidanceAcceptanceResponse,
  OwnedAgentGuidedSessionResponse,
  OwnedAgentOverrideAcceptanceResponse,
  PlayerMatchState,
  ResourceState,
  TreatyActionAcceptanceResponse,
  TreatyRecord,
  UnknownField,
  VictoryState,
  VisibleArmyState,
  VisibleCityState,
  WorldMessageRecord
} from "../types";
import { isRecord } from "./account-session";

export const MATCH_LOBBY_ERROR_MESSAGE =
  "Unable to complete the requested lobby action right now.";
export const COMMAND_SUBMISSION_ERROR_MESSAGE = "Unable to submit orders right now.";
export const MESSAGE_SUBMISSION_ERROR_MESSAGE = "Unable to submit message right now.";
export const GROUP_CHAT_CREATE_ERROR_MESSAGE = "Unable to create group chat right now.";
export const DIPLOMACY_SUBMISSION_ERROR_MESSAGE = "Unable to submit diplomacy action right now.";
export const GUIDED_AGENT_CONTROLS_ERROR_MESSAGE =
  "Unable to load guided agent controls right now.";

export type ResponseLike = {
  ok: boolean;
  status: number;
  json(): Promise<unknown>;
};

export function isMatchLobbyCreateResponse(payload: unknown): payload is MatchLobbyCreateResponse {
  return isMatchSummary(payload) && typeof (payload as Record<string, unknown>).creator_player_id === "string";
}

export function isMatchJoinResponse(payload: unknown): payload is MatchJoinResponse {
  return (
    isRecord(payload) &&
    payload.status === "accepted" &&
    typeof payload.match_id === "string" &&
    typeof payload.agent_id === "string" &&
    typeof payload.player_id === "string"
  );
}

export function isMatchOrdersCommandEnvelopeResponse(
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

export function isOrderAcceptanceResponse(payload: unknown): payload is OrderAcceptanceResponse {
  return (
    isRecord(payload) &&
    payload.status === "accepted" &&
    typeof payload.match_id === "string" &&
    typeof payload.player_id === "string" &&
    typeof payload.tick === "number" &&
    typeof payload.submission_index === "number"
  );
}

export function isMessageAcceptanceResponse(payload: unknown): payload is MessageAcceptanceResponse {
  return (
    isRecord(payload) &&
    payload.status === "accepted" &&
    typeof payload.match_id === "string" &&
    typeof payload.message_id === "number" &&
    (payload.channel === "world" || payload.channel === "direct") &&
    typeof payload.sender_id === "string" &&
    (typeof payload.recipient_id === "string" || payload.recipient_id === null) &&
    typeof payload.tick === "number" &&
    typeof payload.content === "string"
  );
}

export function isGroupChatMessageAcceptanceResponse(
  payload: unknown
): payload is GroupChatMessageAcceptanceResponse {
  return (
    isRecord(payload) &&
    payload.status === "accepted" &&
    typeof payload.match_id === "string" &&
    typeof payload.group_chat_id === "string" &&
    isGroupMessageRecord(payload.message) &&
    payload.message.group_chat_id === payload.group_chat_id
  );
}

export function isGroupChatCreateAcceptanceResponse(
  payload: unknown
): payload is GroupChatCreateAcceptanceResponse {
  return (
    isRecord(payload) &&
    payload.status === "accepted" &&
    typeof payload.match_id === "string" &&
    isGroupChatRecord(payload.group_chat)
  );
}

export function isTreatyActionAcceptanceResponse(
  payload: unknown
): payload is TreatyActionAcceptanceResponse {
  return (
    isRecord(payload) &&
    payload.status === "accepted" &&
    typeof payload.match_id === "string" &&
    isTreatyRecord(payload.treaty)
  );
}

export function isAllianceActionAcceptanceResponse(
  payload: unknown
): payload is AllianceActionAcceptanceResponse {
  return (
    isRecord(payload) &&
    payload.status === "accepted" &&
    typeof payload.match_id === "string" &&
    typeof payload.player_id === "string" &&
    isAllianceRecord(payload.alliance)
  );
}

export function isOwnedAgentGuidedSessionResponse(
  payload: unknown
): payload is OwnedAgentGuidedSessionResponse {
  return (
    isRecord(payload) &&
    typeof payload.match_id === "string" &&
    typeof payload.agent_id === "string" &&
    typeof payload.player_id === "string" &&
    isPlayerMatchState(payload.state) &&
    isOrderBatch(payload.queued_orders) &&
    Array.isArray(payload.guidance) &&
    payload.guidance.every(isGuidedSessionGuidanceRecord) &&
    Array.isArray(payload.group_chats) &&
    payload.group_chats.every(isGroupChatRecord) &&
    isAgentBriefingMessageBuckets(payload.messages) &&
    isGuidedSessionRecentActivity(payload.recent_activity)
  );
}

export function isOwnedAgentGuidanceAcceptanceResponse(
  payload: unknown
): payload is OwnedAgentGuidanceAcceptanceResponse {
  return (
    isRecord(payload) &&
    payload.status === "accepted" &&
    typeof payload.guidance_id === "string" &&
    typeof payload.match_id === "string" &&
    typeof payload.agent_id === "string" &&
    typeof payload.player_id === "string" &&
    typeof payload.tick === "number" &&
    typeof payload.content === "string"
  );
}

export function isOwnedAgentOverrideAcceptanceResponse(
  payload: unknown
): payload is OwnedAgentOverrideAcceptanceResponse {
  return (
    isRecord(payload) &&
    payload.status === "accepted" &&
    typeof payload.override_id === "string" &&
    typeof payload.match_id === "string" &&
    typeof payload.agent_id === "string" &&
    typeof payload.player_id === "string" &&
    typeof payload.tick === "number" &&
    typeof payload.submission_index === "number" &&
    typeof payload.superseded_submission_count === "number" &&
    isOrderBatch(payload.orders)
  );
}

export function isMatchSummary(payload: unknown): payload is MatchSummary {
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

function isAgentBriefingMessageBuckets(payload: unknown): payload is {
  world: WorldMessageRecord[];
  direct: DirectMessageRecord[];
  group: GroupMessageRecord[];
} {
  return (
    isRecord(payload) &&
    Array.isArray(payload.world) &&
    payload.world.every(isWorldMessageRecord) &&
    Array.isArray(payload.direct) &&
    payload.direct.every(isDirectMessageRecord) &&
    Array.isArray(payload.group) &&
    payload.group.every(isGroupMessageRecord)
  );
}

function isOrderBatch(payload: unknown): payload is {
  movements: { army_id: string; destination: string }[];
  recruitment: { city: string; troops: number }[];
  upgrades: { city: string; track: string; target_tier: number }[];
  transfers: { to: string; resource: string; amount: number }[];
} {
  return (
    isRecord(payload) &&
    Array.isArray(payload.movements) &&
    payload.movements.every(isMovementOrder) &&
    Array.isArray(payload.recruitment) &&
    payload.recruitment.every(isRecruitmentOrder) &&
    Array.isArray(payload.upgrades) &&
    payload.upgrades.every(isUpgradeOrder) &&
    Array.isArray(payload.transfers) &&
    payload.transfers.every(isTransferOrder)
  );
}

function isMovementOrder(payload: unknown): payload is { army_id: string; destination: string } {
  return isRecord(payload) && typeof payload.army_id === "string" && typeof payload.destination === "string";
}

function isRecruitmentOrder(payload: unknown): payload is { city: string; troops: number } {
  return isRecord(payload) && typeof payload.city === "string" && typeof payload.troops === "number";
}

function isUpgradeOrder(payload: unknown): payload is {
  city: string;
  track: string;
  target_tier: number;
} {
  return (
    isRecord(payload) &&
    typeof payload.city === "string" &&
    typeof payload.track === "string" &&
    typeof payload.target_tier === "number"
  );
}

function isTransferOrder(payload: unknown): payload is { to: string; resource: string; amount: number } {
  return (
    isRecord(payload) &&
    typeof payload.to === "string" &&
    typeof payload.resource === "string" &&
    typeof payload.amount === "number"
  );
}

function isGuidedSessionGuidanceRecord(payload: unknown): payload is GuidedSessionGuidanceRecord {
  return (
    isRecord(payload) &&
    typeof payload.guidance_id === "string" &&
    typeof payload.match_id === "string" &&
    typeof payload.player_id === "string" &&
    typeof payload.tick === "number" &&
    typeof payload.content === "string" &&
    typeof payload.created_at === "string"
  );
}

function isGuidedSessionRecentActivity(payload: unknown): payload is {
  alliances: AllianceRecord[];
  treaties: TreatyRecord[];
} {
  return (
    isRecord(payload) &&
    Array.isArray(payload.alliances) &&
    payload.alliances.every(isAllianceRecord) &&
    Array.isArray(payload.treaties) &&
    payload.treaties.every(isTreatyRecord)
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
