import type {
  AllianceMemberRecord,
  AllianceRecord,
  ApiErrorEnvelope,
  BuildingQueueItem,
  CityUpgradeState,
  DirectMessageRecord,
  GroupChatRecord,
  GroupMessageRecord,
  PlayerMatchEnvelope,
  PlayerMatchState,
  ResourceState,
  SpectatorArmyState,
  SpectatorCityState,
  SpectatorMatchEnvelope,
  SpectatorMatchState,
  SpectatorPlayerState,
  TreatyRecord,
  UnknownField,
  VictoryState,
  VisibleArmyState,
  VisibleCityState,
  WorldMessageRecord
} from "../types";
import { isApiErrorEnvelope, isRecord } from "./public-contract-shared";

const PLAYER_MATCH_UPDATE_ERROR_MESSAGE = "Unable to parse player live match update.";
const SPECTATOR_MATCH_UPDATE_ERROR_MESSAGE = "Unable to parse spectator live match update.";

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
