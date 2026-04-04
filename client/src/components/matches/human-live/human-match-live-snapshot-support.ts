import type {
  AllianceAction,
  AllianceActionAcceptanceResponse,
  AllianceActionRequest,
  AllianceRecord,
  GroupChatCreateAcceptanceResponse,
  GroupChatMessageAcceptanceResponse,
  GroupChatRecord,
  MatchOrdersCommandRequest,
  MessageAcceptanceResponse,
  PlayerMatchEnvelope,
  TreatyActionAcceptanceResponse,
  VisibleArmyState
} from "../../../lib/types";
import type { BritainMapLayout } from "../../../lib/britain-map";
import type { MatchLiveMapArmyDatum, MatchLiveMapCityDatum } from "../match-live-map";
import type {
  AllianceDraftState,
  GroupChatCreateDraftState,
  MapSelection,
  MessageDraftState,
  MovementDraft,
  OrderDraftState,
  RecruitmentDraft,
  TransferDraft,
  TreatyDraftState,
  UpgradeDraft
} from "./human-match-live-types";

export const emptyDraftState = (): OrderDraftState => ({
  movements: [],
  recruitment: [],
  upgrades: [],
  transfers: []
});

export const emptyMovementDraft = (): MovementDraft => ({
  armyId: "",
  destination: ""
});

export const emptyRecruitmentDraft = (): RecruitmentDraft => ({
  city: "",
  troops: ""
});

export const emptyUpgradeDraft = (): UpgradeDraft => ({
  city: "",
  track: "economy",
  targetTier: ""
});

export const emptyTransferDraft = (): TransferDraft => ({
  to: "",
  resource: "food",
  amount: ""
});

export function formatCityName(cityId: string) {
  return cityId.charAt(0).toUpperCase() + cityId.slice(1);
}

export const emptyMessageDraft = (
  directTargetIds: string[],
  visibleGroupChats: GroupChatRecord[]
): MessageDraftState => ({
  channel: "world",
  directRecipientId: directTargetIds[0] ?? "",
  groupChatId: visibleGroupChats[0]?.group_chat_id ?? "",
  content: ""
});

export const emptyTreatyDraft = (counterpartyIds: string[]): TreatyDraftState => ({
  action: "propose",
  treatyType: "non_aggression",
  counterpartyId: counterpartyIds[0] ?? ""
});

export const emptyAllianceDraft = (joinableAlliances: AllianceRecord[]): AllianceDraftState => ({
  action: "create",
  name: "",
  allianceId: joinableAlliances[0]?.alliance_id ?? ""
});

export const emptyGroupChatCreateDraft = (): GroupChatCreateDraftState => ({
  name: "",
  selectedInviteeIds: []
});

function parsePositiveInteger(value: string): number | null {
  const trimmedValue = value.trim();
  if (trimmedValue.length === 0) {
    return null;
  }

  const parsedValue = Number(trimmedValue);
  if (!Number.isInteger(parsedValue) || parsedValue <= 0) {
    return null;
  }

  return parsedValue;
}

export function buildOrderRequest(
  envelope: PlayerMatchEnvelope,
  drafts: OrderDraftState
):
  | { ok: true; request: MatchOrdersCommandRequest }
  | { ok: false; message: string } {
  if (
    drafts.movements.length === 0 &&
    drafts.recruitment.length === 0 &&
    drafts.upgrades.length === 0 &&
    drafts.transfers.length === 0
  ) {
    return { ok: false, message: "Add at least one order draft before submitting." };
  }

  const movements = drafts.movements.map((draft, index) => {
    const armyId = draft.armyId.trim();
    const destination = draft.destination.trim();
    if (armyId.length === 0 || destination.length === 0) {
      return { ok: false as const, message: `Movement order ${index + 1} requires army ID and destination.` };
    }
    return { ok: true as const, value: { army_id: armyId, destination } };
  });
  const invalidMovement = movements.find((draft) => !draft.ok);
  if (invalidMovement && !invalidMovement.ok) {
    return { ok: false, message: invalidMovement.message };
  }

  const recruitment = drafts.recruitment.map((draft, index) => {
    const city = draft.city.trim();
    const troops = parsePositiveInteger(draft.troops);
    if (city.length === 0 || troops === null) {
      return { ok: false as const, message: `Recruitment order ${index + 1} requires city and troops greater than zero.` };
    }
    return { ok: true as const, value: { city, troops } };
  });
  const invalidRecruitment = recruitment.find((draft) => !draft.ok);
  if (invalidRecruitment && !invalidRecruitment.ok) {
    return { ok: false, message: invalidRecruitment.message };
  }

  const upgrades = drafts.upgrades.map((draft, index) => {
    const city = draft.city.trim();
    const targetTier = parsePositiveInteger(draft.targetTier);
    if (city.length === 0 || targetTier === null) {
      return { ok: false as const, message: `Upgrade order ${index + 1} requires city and target tier greater than zero.` };
    }
    return { ok: true as const, value: { city, track: draft.track, target_tier: targetTier } };
  });
  const invalidUpgrade = upgrades.find((draft) => !draft.ok);
  if (invalidUpgrade && !invalidUpgrade.ok) {
    return { ok: false, message: invalidUpgrade.message };
  }

  const transfers = drafts.transfers.map((draft, index) => {
    const to = draft.to.trim();
    const amount = parsePositiveInteger(draft.amount);
    if (to.length === 0 || amount === null) {
      return { ok: false as const, message: `Transfer order ${index + 1} requires destination and amount greater than zero.` };
    }
    return { ok: true as const, value: { to, resource: draft.resource, amount } };
  });
  const invalidTransfer = transfers.find((draft) => !draft.ok);
  if (invalidTransfer && !invalidTransfer.ok) {
    return { ok: false, message: invalidTransfer.message };
  }

  return {
    ok: true,
    request: {
      match_id: envelope.data.match_id,
      tick: envelope.data.state.tick,
      orders: {
        movements: movements.flatMap((draft) => (draft.ok ? [draft.value] : [])),
        recruitment: recruitment.flatMap((draft) => (draft.ok ? [draft.value] : [])),
        upgrades: upgrades.flatMap((draft) => (draft.ok ? [draft.value] : [])),
        transfers: transfers.flatMap((draft) => (draft.ok ? [draft.value] : []))
      }
    }
  };
}

export function collectVisiblePlayerIds(envelope: PlayerMatchEnvelope): string[] {
  const visiblePlayerIds = new Set<string>();
  const addPlayerId = (playerId: string | null | undefined) => {
    if (!playerId || playerId === envelope.data.player_id) {
      return;
    }
    visiblePlayerIds.add(playerId);
  };

  Object.values(envelope.data.state.cities).forEach((city) => addPlayerId(city.owner));
  envelope.data.state.visible_armies.forEach((army) => addPlayerId(army.owner));
  envelope.data.state.alliance_members.forEach((playerId) => addPlayerId(playerId));
  envelope.data.world_messages.forEach((message) => addPlayerId(message.sender_id));
  envelope.data.direct_messages.forEach((message) => {
    addPlayerId(message.sender_id);
    addPlayerId(message.recipient_id);
  });
  envelope.data.group_chats.forEach((groupChat) => {
    addPlayerId(groupChat.created_by);
    groupChat.member_ids.forEach((playerId) => addPlayerId(playerId));
  });
  envelope.data.group_messages.forEach((message) => addPlayerId(message.sender_id));
  envelope.data.treaties.forEach((treaty) => {
    addPlayerId(treaty.player_a_id);
    addPlayerId(treaty.player_b_id);
  });
  envelope.data.alliances.forEach((alliance) => {
    addPlayerId(alliance.leader_id);
    alliance.members.forEach((member) => addPlayerId(member.player_id));
  });

  return Array.from(visiblePlayerIds).sort((left, right) => left.localeCompare(right));
}

export function describeAcceptedMessage(
  accepted: MessageAcceptanceResponse | GroupChatMessageAcceptanceResponse
): string {
  if ("group_chat_id" in accepted) {
    return `Accepted group message ${accepted.message.message_id} in ${accepted.group_chat_id} for tick ${accepted.message.tick} from ${accepted.message.sender_id}.`;
  }

  return `Accepted ${accepted.channel} message ${accepted.message_id} for tick ${accepted.tick} from ${accepted.sender_id}.`;
}

export function describeAcceptedGroupChatCreate(
  accepted: GroupChatCreateAcceptanceResponse
): { message: string; details: string[] } {
  return {
    message: `Group chat accepted: ${accepted.group_chat.name}.`,
    details: [
      `Group chat id: ${accepted.group_chat.group_chat_id}`,
      `Created by: ${accepted.group_chat.created_by}`,
      `Created tick: ${accepted.group_chat.created_tick}`,
      `Members: ${accepted.group_chat.member_ids.join(", ")}`
    ]
  };
}

export function collectJoinableAlliances(envelope: PlayerMatchEnvelope): AllianceRecord[] {
  return envelope.data.alliances.filter(
    (alliance) => !alliance.members.some((member) => member.player_id === envelope.data.player_id)
  );
}

export function getSelectionOwnerCounterparty(
  selection: MapSelection | null,
  currentPlayerId: string,
  selectedCity: MatchLiveMapCityDatum | null,
  selectedArmy: MatchLiveMapArmyDatum | null
): string | null {
  if (selection === null) {
    return null;
  }

  const ownerLabel = selection.kind === "city" ? selectedCity?.ownerLabel ?? null : selectedArmy?.ownerLabel ?? null;
  if (ownerLabel === null || ownerLabel === currentPlayerId) {
    return null;
  }

  return ownerLabel;
}

export function describeAcceptedTreaty(
  accepted: TreatyActionAcceptanceResponse,
  currentPlayerId: string
): { message: string; details: string[] } {
  const counterpartyId =
    accepted.treaty.player_a_id === currentPlayerId ? accepted.treaty.player_b_id : accepted.treaty.player_a_id;

  return {
    message: `Treaty accepted: ${accepted.treaty.treaty_type} with ${counterpartyId}.`,
    details: [
      `Treaty id: ${accepted.treaty.treaty_id}`,
      `Counterparties: ${accepted.treaty.player_a_id} and ${accepted.treaty.player_b_id}`,
      `Type: ${accepted.treaty.treaty_type}`,
      `Status: ${accepted.treaty.status}`,
      `Proposed by: ${accepted.treaty.proposed_by}`,
      `Proposed tick: ${accepted.treaty.proposed_tick}`,
      accepted.treaty.signed_tick === null
        ? "Signed tick: not signed"
        : `Signed tick: ${accepted.treaty.signed_tick}`
    ]
  };
}

export function describeAcceptedAlliance(
  accepted: AllianceActionAcceptanceResponse,
  action: AllianceAction
): { message: string; details: string[] } {
  const joinedMember =
    accepted.alliance.members.find((member) => member.player_id === accepted.player_id) ?? null;
  const actionLabel =
    action === "create" ? "created" : action === "join" ? "joined" : "left";

  return {
    message: `Alliance accepted: ${actionLabel} ${accepted.alliance.name}.`,
    details: [
      `Action: ${action}`,
      `Player id: ${accepted.player_id}`,
      `Alliance id: ${accepted.alliance.alliance_id}`,
      `Alliance name: ${accepted.alliance.name}`,
      `Leader id: ${accepted.alliance.leader_id}`,
      `Formed tick: ${accepted.alliance.formed_tick}`,
      joinedMember === null
        ? `Accepted player membership: ${accepted.player_id} not present in accepted alliance record`
        : `Accepted player joined tick: ${joinedMember.joined_tick}`
    ]
  };
}

export function buildHumanLiveSnapshotViewModel(
  envelope: PlayerMatchEnvelope,
  mapLayout: BritainMapLayout
) {
  const latestWorldMessage = envelope.data.world_messages.at(-1) ?? null;
  const latestDirectMessage = envelope.data.direct_messages.at(-1) ?? null;
  const latestGroupChat = envelope.data.group_chats.at(-1) ?? null;
  const latestGroupMessage = envelope.data.group_messages.at(-1) ?? null;
  const latestTreaty = envelope.data.treaties.at(-1) ?? null;
  const latestAlliance = envelope.data.alliances.at(-1) ?? null;
  const partialArmy = envelope.data.state.visible_armies.find((army) => army.visibility === "partial") ?? null;
  const mapCities: MatchLiveMapCityDatum[] = Object.entries(envelope.data.state.cities)
    .map(([cityId, city]) => ({
      cityId,
      cityName: formatCityName(cityId),
      ownerLabel: city.visibility === "full" ? city.owner : null,
      ownerVisibility: city.visibility,
      garrisonLabel: city.visibility === "full" && city.garrison !== "unknown" ? String(city.garrison) : null
    }))
    .sort((left, right) => left.cityName.localeCompare(right.cityName));
  const mapArmies = envelope.data.state.visible_armies
    .map((army) => {
      const cityId = army.location ?? army.destination;

      if (cityId === null) {
        return null;
      }

      return {
        armyId: army.id,
        cityId,
        cityName: formatCityName(cityId),
        ownerLabel: army.owner,
        troopsLabel: army.visibility === "full" && army.troops !== "unknown" ? String(army.troops) : null,
        visibility: army.visibility,
        visibleLocationCityId: army.visibility === "full" ? (army.location ?? army.destination) : null,
        transit: {
          status: army.ticks_remaining > 0 ? "in_transit" : "stationary",
          ticksRemaining: army.ticks_remaining,
          destinationCityId:
            army.visibility === "full" && typeof army.destination === "string" ? army.destination : null,
          pathCityIds:
            army.visibility === "full" && Array.isArray(army.path) ? army.path : null
        }
      };
    })
    .filter((army): army is MatchLiveMapArmyDatum => army !== null)
    .sort((left, right) => left.cityName.localeCompare(right.cityName));
  const cityNamesById = new Map(mapLayout.cities.map((city) => [city.id, city.name]));

  return {
    latestWorldMessage,
    latestDirectMessage,
    latestGroupChat,
    latestGroupMessage,
    latestTreaty,
    latestAlliance,
    partialArmy,
    mapCities,
    mapArmies,
    cityNamesById
  };
}

export function buildAllianceActionRequest(
  envelope: PlayerMatchEnvelope,
  allianceDraft: AllianceDraftState
):
  | { ok: true; request: AllianceActionRequest }
  | { ok: false; message: string } {
  if (allianceDraft.action === "create") {
    const name = allianceDraft.name.trim();
    if (name.length === 0) {
      return {
        ok: false,
        message: "Alliance name is required before creating an alliance."
      };
    }

    return {
      ok: true,
      request: { match_id: envelope.data.match_id, action: "create", name }
    };
  }

  if (allianceDraft.action === "join") {
    if (allianceDraft.allianceId.length === 0) {
      return {
        ok: false,
        message: "Choose a visible alliance before joining."
      };
    }

    return {
      ok: true,
      request: {
        match_id: envelope.data.match_id,
        action: "join",
        alliance_id: allianceDraft.allianceId
      }
    };
  }

  return {
    ok: true,
    request: { match_id: envelope.data.match_id, action: "leave" }
  };
}
