"use client";

import { useEffect, useState } from "react";
import {
  CommandSubmissionError,
  DiplomacySubmissionError,
  GroupChatCreateError,
  MessageSubmissionError,
  submitAllianceAction,
  submitGroupChatCreate,
  submitGroupChatMessage,
  submitMatchMessage,
  submitMatchOrders,
  submitTreatyAction
} from "../../../lib/api";
import type {
  AllianceRecord,
  AllianceAction,
  AllianceActionAcceptanceResponse,
  AllianceActionRequest,
  GroupChatRecord,
  GroupChatCreateAcceptanceResponse,
  GroupChatMessageAcceptanceResponse,
  GroupMessageRecord,
  MessageAcceptanceResponse,
  MatchOrdersCommandRequest,
  PlayerMatchEnvelope,
  ResourceType,
  TreatyAction,
  TreatyActionAcceptanceResponse,
  TreatyRecord,
  TreatyType,
  UpgradeTrack,
  VisibleArmyState
} from "../../../lib/types";
import type { BritainMapLayout } from "../../../lib/britain-map";
import {
  MatchLiveMap,
  describeTransitListText,
  type MatchLiveMapArmyDatum,
  type MatchLiveMapCityDatum
} from "../match-live-map";

type MovementDraft = {
  armyId: string;
  destination: string;
};

type RecruitmentDraft = {
  city: string;
  troops: string;
};

type UpgradeDraft = {
  city: string;
  track: UpgradeTrack;
  targetTier: string;
};

type TransferDraft = {
  to: string;
  resource: ResourceType;
  amount: string;
};

type OrderDraftState = {
  movements: MovementDraft[];
  recruitment: RecruitmentDraft[];
  upgrades: UpgradeDraft[];
  transfers: TransferDraft[];
};

type MapSelection =
  | { kind: "city"; cityId: string }
  | { kind: "army"; armyId: string };

type SubmissionFeedback =
  | {
      status: "idle";
    }
  | {
      status: "submitting";
    }
  | {
      status: "success";
      message: string;
    }
  | {
      status: "error";
      message: string;
      code: string;
      statusCode: number;
    };

type LiveMessagingChannel = "world" | "direct" | "group";

type MessageDraftState = {
  channel: LiveMessagingChannel;
  directRecipientId: string;
  groupChatId: string;
  content: string;
};

type GroupChatCreateDraftState = {
  name: string;
  selectedInviteeIds: string[];
};

type AsyncSubmissionFeedback =
  | {
      status: "idle";
    }
  | {
      status: "submitting";
    }
  | {
      status: "success";
      message: string;
      details?: string[];
    }
  | {
      status: "error";
      message: string;
      code: string;
      statusCode: number;
    };

type TreatyDraftState = {
  action: TreatyAction;
  treatyType: TreatyType;
  counterpartyId: string;
};

type AllianceDraftState = {
  action: AllianceAction;
  name: string;
  allianceId: string;
};

const resourceRows: Array<{
  label: string;
  value: (envelope: PlayerMatchEnvelope) => number | string;
}> = [
  { label: "Food", value: (envelope) => envelope.data.state.resources.food },
  { label: "Production", value: (envelope) => envelope.data.state.resources.production },
  { label: "Money", value: (envelope) => envelope.data.state.resources.money }
];

const emptyDraftState = (): OrderDraftState => ({
  movements: [],
  recruitment: [],
  upgrades: [],
  transfers: []
});

const emptyMovementDraft = (): MovementDraft => ({
  armyId: "",
  destination: ""
});

const emptyRecruitmentDraft = (): RecruitmentDraft => ({
  city: "",
  troops: ""
});

const emptyUpgradeDraft = (): UpgradeDraft => ({
  city: "",
  track: "economy",
  targetTier: ""
});

const emptyTransferDraft = (): TransferDraft => ({
  to: "",
  resource: "food",
  amount: ""
});

function formatCityName(cityId: string) {
  return cityId.charAt(0).toUpperCase() + cityId.slice(1);
}

const emptyMessageDraft = (
  directTargetIds: string[],
  visibleGroupChats: GroupChatRecord[]
): MessageDraftState => ({
  channel: "world",
  directRecipientId: directTargetIds[0] ?? "",
  groupChatId: visibleGroupChats[0]?.group_chat_id ?? "",
  content: ""
});

const emptyTreatyDraft = (counterpartyIds: string[]): TreatyDraftState => ({
  action: "propose",
  treatyType: "non_aggression",
  counterpartyId: counterpartyIds[0] ?? ""
});

const emptyAllianceDraft = (joinableAlliances: AllianceRecord[]): AllianceDraftState => ({
  action: "create",
  name: "",
  allianceId: joinableAlliances[0]?.alliance_id ?? ""
});

const emptyGroupChatCreateDraft = (): GroupChatCreateDraftState => ({
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

function buildOrderRequest(
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

function collectVisiblePlayerIds(envelope: PlayerMatchEnvelope): string[] {
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

function describeAcceptedMessage(
  accepted: MessageAcceptanceResponse | GroupChatMessageAcceptanceResponse
): string {
  if ("group_chat_id" in accepted) {
    return `Accepted group message ${accepted.message.message_id} in ${accepted.group_chat_id} for tick ${accepted.message.tick} from ${accepted.message.sender_id}.`;
  }

  return `Accepted ${accepted.channel} message ${accepted.message_id} for tick ${accepted.tick} from ${accepted.sender_id}.`;
}

function describeAcceptedGroupChatCreate(
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

function collectJoinableAlliances(envelope: PlayerMatchEnvelope): AllianceRecord[] {
  return envelope.data.alliances.filter(
    (alliance) => !alliance.members.some((member) => member.player_id === envelope.data.player_id)
  );
}

function getSelectionOwnerCounterparty(
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

function describeAcceptedTreaty(
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

function describeAcceptedAlliance(
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

export function HumanMatchLiveSnapshot({
  envelope,
  mapLayout,
  apiBaseUrl,
  bearerToken,
  liveStatus
}: {
  envelope: PlayerMatchEnvelope;
  mapLayout: BritainMapLayout;
  apiBaseUrl: string;
  bearerToken: string | null;
  liveStatus: "live" | "not_live";
}) {
  const [drafts, setDrafts] = useState<OrderDraftState>(() => emptyDraftState());
  const [submissionFeedback, setSubmissionFeedback] = useState<SubmissionFeedback>({
    status: "idle"
  });
  const [selectedMapEntity, setSelectedMapEntity] = useState<MapSelection | null>(null);
  const [selectionGuidance, setSelectionGuidance] = useState<string | null>(null);
  const visiblePlayerIds = collectVisiblePlayerIds(envelope);
  const directTargetIds = visiblePlayerIds;
  const visibleGroupChats = envelope.data.group_chats;
  const treatyCounterpartyIds = visiblePlayerIds;
  const joinableAlliances = collectJoinableAlliances(envelope);
  const [messageDraft, setMessageDraft] = useState<MessageDraftState>(() =>
    emptyMessageDraft(directTargetIds, visibleGroupChats)
  );
  const [messageSubmissionFeedback, setMessageSubmissionFeedback] = useState<AsyncSubmissionFeedback>({
    status: "idle"
  });
  const [groupChatCreateDraft, setGroupChatCreateDraft] = useState<GroupChatCreateDraftState>(() =>
    emptyGroupChatCreateDraft()
  );
  const [groupChatCreateFeedback, setGroupChatCreateFeedback] = useState<AsyncSubmissionFeedback>({
    status: "idle"
  });
  const [treatyDraft, setTreatyDraft] = useState<TreatyDraftState>(() =>
    emptyTreatyDraft(treatyCounterpartyIds)
  );
  const [treatySubmissionFeedback, setTreatySubmissionFeedback] = useState<AsyncSubmissionFeedback>({
    status: "idle"
  });
  const [allianceDraft, setAllianceDraft] = useState<AllianceDraftState>(() =>
    emptyAllianceDraft(joinableAlliances)
  );
  const [allianceSubmissionFeedback, setAllianceSubmissionFeedback] = useState<AsyncSubmissionFeedback>({
    status: "idle"
  });
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
  const selectedCity =
    selectedMapEntity?.kind === "city"
      ? mapCities.find((city) => city.cityId === selectedMapEntity.cityId) ?? null
      : null;
  const selectedArmy =
    selectedMapEntity?.kind === "army"
      ? mapArmies.find((army) => army.armyId === selectedMapEntity.armyId) ?? null
      : null;
  const selectedCounterpartyId = getSelectionOwnerCounterparty(
    selectedMapEntity,
    envelope.data.player_id,
    selectedCity,
    selectedArmy
  );
  const canSubmit = liveStatus === "live" && bearerToken !== null && submissionFeedback.status !== "submitting";
  const canSubmitMessage =
    liveStatus === "live" && bearerToken !== null && messageSubmissionFeedback.status !== "submitting";
  const canSubmitGroupChatCreate =
    liveStatus === "live" &&
    bearerToken !== null &&
    groupChatCreateFeedback.status !== "submitting" &&
    groupChatCreateDraft.name.trim().length > 0 &&
    groupChatCreateDraft.selectedInviteeIds.length > 0 &&
    visiblePlayerIds.length > 0;
  const canSubmitTreaty =
    liveStatus === "live" && bearerToken !== null && treatySubmissionFeedback.status !== "submitting";
  const canSubmitAlliance =
    liveStatus === "live" && bearerToken !== null && allianceSubmissionFeedback.status !== "submitting";

  useEffect(() => {
    setMessageDraft((currentDraft) => {
      const nextChannel =
        currentDraft.channel === "direct" && directTargetIds.length === 0
          ? "world"
          : currentDraft.channel === "group" && visibleGroupChats.length === 0
            ? "world"
            : currentDraft.channel;
      const nextDirectRecipientId = directTargetIds.includes(currentDraft.directRecipientId)
        ? currentDraft.directRecipientId
        : (directTargetIds[0] ?? "");
      const nextGroupChatId = visibleGroupChats.some(
        (groupChat) => groupChat.group_chat_id === currentDraft.groupChatId
      )
        ? currentDraft.groupChatId
        : (visibleGroupChats[0]?.group_chat_id ?? "");

      if (
        nextChannel === currentDraft.channel &&
        nextDirectRecipientId === currentDraft.directRecipientId &&
        nextGroupChatId === currentDraft.groupChatId
      ) {
        return currentDraft;
      }

      return {
        ...currentDraft,
        channel: nextChannel,
        directRecipientId: nextDirectRecipientId,
        groupChatId: nextGroupChatId
      };
    });
  }, [directTargetIds, visibleGroupChats]);

  useEffect(() => {
    setGroupChatCreateDraft((currentDraft) => {
      const nextSelectedInviteeIds = currentDraft.selectedInviteeIds.filter((playerId) =>
        visiblePlayerIds.includes(playerId)
      );

      if (nextSelectedInviteeIds.length === currentDraft.selectedInviteeIds.length) {
        return currentDraft;
      }

      return {
        ...currentDraft,
        selectedInviteeIds: nextSelectedInviteeIds
      };
    });
  }, [visiblePlayerIds]);

  useEffect(() => {
    setTreatyDraft((currentDraft) => {
      const nextCounterpartyId = treatyCounterpartyIds.includes(currentDraft.counterpartyId)
        ? currentDraft.counterpartyId
        : (treatyCounterpartyIds[0] ?? "");

      if (nextCounterpartyId === currentDraft.counterpartyId) {
        return currentDraft;
      }

      return {
        ...currentDraft,
        counterpartyId: nextCounterpartyId
      };
    });
  }, [treatyCounterpartyIds]);

  useEffect(() => {
    setAllianceDraft((currentDraft) => {
      const nextAllianceId = joinableAlliances.some(
        (alliance) => alliance.alliance_id === currentDraft.allianceId
      )
        ? currentDraft.allianceId
        : (joinableAlliances[0]?.alliance_id ?? "");

      if (nextAllianceId === currentDraft.allianceId) {
        return currentDraft;
      }

      return {
        ...currentDraft,
        allianceId: nextAllianceId
      };
    });
  }, [joinableAlliances]);

  useEffect(() => {
    if (selectedMapEntity === null) {
      return;
    }

    if (
      selectedMapEntity.kind === "city" &&
      mapCities.some((city) => city.cityId === selectedMapEntity.cityId)
    ) {
      return;
    }

    if (
      selectedMapEntity.kind === "army" &&
      mapArmies.some((army) => army.armyId === selectedMapEntity.armyId)
    ) {
      return;
    }

    setSelectedMapEntity(null);
    setSelectionGuidance("The previous map selection is no longer visible in the current snapshot.");
  }, [mapArmies, mapCities, selectedMapEntity]);

  const updateMovementDraft = (index: number, key: keyof MovementDraft, value: string) => {
    setSelectionGuidance(null);
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      movements: currentDrafts.movements.map((draft, draftIndex) =>
        draftIndex === index ? { ...draft, [key]: value } : draft
      )
    }));
  };

  const updateRecruitmentDraft = (index: number, key: keyof RecruitmentDraft, value: string) => {
    setSelectionGuidance(null);
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      recruitment: currentDrafts.recruitment.map((draft, draftIndex) =>
        draftIndex === index ? { ...draft, [key]: value } : draft
      )
    }));
  };

  const updateUpgradeDraft = (index: number, key: keyof UpgradeDraft, value: string) => {
    setSelectionGuidance(null);
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      upgrades: currentDrafts.upgrades.map((draft, draftIndex) =>
        draftIndex === index ? { ...draft, [key]: value } : draft
      )
    }));
  };

  const updateTransferDraft = (index: number, key: keyof TransferDraft, value: string) => {
    setSelectionGuidance(null);
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      transfers: currentDrafts.transfers.map((draft, draftIndex) =>
        draftIndex === index ? { ...draft, [key]: value } : draft
      )
    }));
  };

  const addMovementDraft = () => {
    setSubmissionFeedback({ status: "idle" });
    setSelectionGuidance(null);
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      movements: [...currentDrafts.movements, emptyMovementDraft()]
    }));
  };

  const addRecruitmentDraft = () => {
    setSubmissionFeedback({ status: "idle" });
    setSelectionGuidance(null);
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      recruitment: [...currentDrafts.recruitment, emptyRecruitmentDraft()]
    }));
  };

  const addUpgradeDraft = () => {
    setSubmissionFeedback({ status: "idle" });
    setSelectionGuidance(null);
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      upgrades: [...currentDrafts.upgrades, emptyUpgradeDraft()]
    }));
  };

  const addTransferDraft = () => {
    setSubmissionFeedback({ status: "idle" });
    setSelectionGuidance(null);
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      transfers: [...currentDrafts.transfers, emptyTransferDraft()]
    }));
  };

  const removeMovementDraft = (index: number) => {
    setSubmissionFeedback({ status: "idle" });
    setSelectionGuidance(null);
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      movements: currentDrafts.movements.filter((_, draftIndex) => draftIndex !== index)
    }));
  };

  const removeRecruitmentDraft = (index: number) => {
    setSubmissionFeedback({ status: "idle" });
    setSelectionGuidance(null);
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      recruitment: currentDrafts.recruitment.filter((_, draftIndex) => draftIndex !== index)
    }));
  };

  const removeUpgradeDraft = (index: number) => {
    setSubmissionFeedback({ status: "idle" });
    setSelectionGuidance(null);
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      upgrades: currentDrafts.upgrades.filter((_, draftIndex) => draftIndex !== index)
    }));
  };

  const removeTransferDraft = (index: number) => {
    setSubmissionFeedback({ status: "idle" });
    setSelectionGuidance(null);
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      transfers: currentDrafts.transfers.filter((_, draftIndex) => draftIndex !== index)
    }));
  };

  const submitDrafts = async () => {
    if (bearerToken === null) {
      setSubmissionFeedback({
        status: "error",
        message: "A stored bearer token is required before submitting orders.",
        code: "auth_missing",
        statusCode: 401
      });
      return;
    }

    const nextRequest = buildOrderRequest(envelope, drafts);
    if (!nextRequest.ok) {
      setSubmissionFeedback({
        status: "error",
        message: nextRequest.message,
        code: "invalid_order_draft",
        statusCode: 400
      });
      return;
    }

    setSubmissionFeedback({ status: "submitting" });

    try {
      const accepted = await submitMatchOrders(nextRequest.request, bearerToken, fetch, { apiBaseUrl });
      setDrafts(emptyDraftState());
      setSubmissionFeedback({
        status: "success",
        message: `Orders accepted for tick ${accepted.tick} from ${accepted.player_id}.`
      });
    } catch (error: unknown) {
      if (error instanceof CommandSubmissionError) {
        setSubmissionFeedback({
          status: "error",
          message: error.message,
          code: error.code,
          statusCode: error.statusCode
        });
        return;
      }

      setSubmissionFeedback({
        status: "error",
        message: "Unable to submit orders right now.",
        code: "command_submission_unavailable",
        statusCode: 500
      });
    }
  };

  const updateMessageDraft = (updates: Partial<MessageDraftState>) => {
    setMessageSubmissionFeedback({ status: "idle" });
    setMessageDraft((currentDraft) => ({
      ...currentDraft,
      ...updates
    }));
  };

  const updateGroupChatCreateDraft = (updates: Partial<GroupChatCreateDraftState>) => {
    setGroupChatCreateFeedback({ status: "idle" });
    setGroupChatCreateDraft((currentDraft) => ({
      ...currentDraft,
      ...updates
    }));
  };

  const updateTreatyDraft = (updates: Partial<TreatyDraftState>) => {
    setTreatySubmissionFeedback({ status: "idle" });
    setTreatyDraft((currentDraft) => ({
      ...currentDraft,
      ...updates
    }));
  };

  const updateAllianceDraft = (updates: Partial<AllianceDraftState>) => {
    setAllianceSubmissionFeedback({ status: "idle" });
    setAllianceDraft((currentDraft) => ({
      ...currentDraft,
      ...updates
    }));
  };

  const selectCity = (city: MatchLiveMapCityDatum) => {
    setSelectedMapEntity({ kind: "city", cityId: city.cityId });
    setSelectionGuidance(null);
  };

  const selectArmy = (army: MatchLiveMapArmyDatum) => {
    setSelectedMapEntity({ kind: "army", armyId: army.armyId });
    setSelectionGuidance(null);
  };

  const setSelectionMessage = (message: string) => {
    setSubmissionFeedback({ status: "idle" });
    setSelectionGuidance(message);
  };

  const applyMovementArmySelection = (index: number) => {
    if (selectedArmy === null) {
      setSelectionMessage(
        `Selection helper could not update movement army ID ${index + 1}: select a visible army first.`
      );
      return;
    }

    updateMovementDraft(index, "armyId", selectedArmy.armyId);
    setSelectionGuidance(`Selection helper set movement army ID ${index + 1} to ${selectedArmy.armyId}.`);
  };

  const applyMovementDestinationSelection = (index: number) => {
    const destination =
      selectedMapEntity?.kind === "city"
        ? selectedCity?.cityId ?? null
        : selectedArmy?.visibleLocationCityId ?? null;

    if (destination === null) {
      const reason =
        selectedMapEntity?.kind === "army"
          ? "the selected army does not expose a visible city."
          : "select a visible city or army first.";
      setSelectionMessage(
        `Selection helper could not update movement destination ${index + 1}: ${reason}`
      );
      return;
    }

    updateMovementDraft(index, "destination", destination);
    setSelectionGuidance(`Selection helper set movement destination ${index + 1} to ${destination}.`);
  };

  const applyRecruitmentCitySelection = (index: number) => {
    if (selectedCity === null) {
      const reason =
        selectedArmy !== null
          ? "the selected army does not expose a visible city."
          : "select a visible city first.";
      setSelectionMessage(`Selection helper could not update recruitment city ${index + 1}: ${reason}`);
      return;
    }

    updateRecruitmentDraft(index, "city", selectedCity.cityId);
    setSelectionGuidance(`Selection helper set recruitment city ${index + 1} to ${selectedCity.cityId}.`);
  };

  const applyUpgradeCitySelection = (index: number) => {
    if (selectedCity === null) {
      const reason =
        selectedArmy !== null
          ? "the selected army does not expose a visible city."
          : "select a visible city first.";
      setSelectionMessage(`Selection helper could not update upgrade city ${index + 1}: ${reason}`);
      return;
    }

    updateUpgradeDraft(index, "city", selectedCity.cityId);
    setSelectionGuidance(`Selection helper set upgrade city ${index + 1} to ${selectedCity.cityId}.`);
  };

  const applyTransferDestinationSelection = (index: number) => {
    if (selectedCounterpartyId === null) {
      const reason =
        selectedMapEntity?.kind === "city"
          ? "visible city selections cannot fill transfer destinations."
          : "the selected marker does not expose a visible counterparty.";
      setSelectionMessage(`Selection helper could not update transfer destination ${index + 1}: ${reason}`);
      return;
    }

    updateTransferDraft(index, "to", selectedCounterpartyId);
    setSelectionGuidance(`Selection helper set transfer destination ${index + 1} to ${selectedCounterpartyId}.`);
  };

  const applyTreatyCounterpartySelection = () => {
    if (selectedCounterpartyId === null) {
      setSelectionMessage(
        "Selection helper could not update treaty counterparty: the selected marker does not expose a visible counterparty."
      );
      return;
    }

    updateTreatyDraft({ counterpartyId: selectedCounterpartyId });
    setSelectionGuidance(`Selection helper set treaty counterparty to ${selectedCounterpartyId}.`);
  };

  const submitMessageDraft = async () => {
    if (bearerToken === null) {
      setMessageSubmissionFeedback({
        status: "error",
        message: "A stored bearer token is required before submitting messages.",
        code: "auth_missing",
        statusCode: 401
      });
      return;
    }

    const content = messageDraft.content.trim();
    if (content.length === 0) {
      setMessageSubmissionFeedback({
        status: "error",
        message: "Message content is required before submitting.",
        code: "invalid_message_draft",
        statusCode: 400
      });
      return;
    }

    if (messageDraft.channel === "direct" && messageDraft.directRecipientId.length === 0) {
      setMessageSubmissionFeedback({
        status: "error",
        message: "Choose a visible direct target before submitting.",
        code: "invalid_message_draft",
        statusCode: 400
      });
      return;
    }

    if (messageDraft.channel === "group" && messageDraft.groupChatId.length === 0) {
      setMessageSubmissionFeedback({
        status: "error",
        message: "Choose a visible group chat before submitting.",
        code: "invalid_message_draft",
        statusCode: 400
      });
      return;
    }

    setMessageSubmissionFeedback({ status: "submitting" });

    try {
      const accepted =
        messageDraft.channel === "group"
          ? await submitGroupChatMessage(
              messageDraft.groupChatId,
              {
                match_id: envelope.data.match_id,
                tick: envelope.data.state.tick,
                content
              },
              bearerToken,
              fetch,
              { apiBaseUrl }
            )
          : await submitMatchMessage(
              {
                match_id: envelope.data.match_id,
                tick: envelope.data.state.tick,
                channel: messageDraft.channel,
                recipient_id: messageDraft.channel === "direct" ? messageDraft.directRecipientId : null,
                content
              },
              bearerToken,
              fetch,
              { apiBaseUrl }
            );

      setMessageDraft((currentDraft) => ({
        ...currentDraft,
        content: ""
      }));
      setMessageSubmissionFeedback({
        status: "success",
        message: describeAcceptedMessage(accepted)
      });
    } catch (error: unknown) {
      if (error instanceof MessageSubmissionError) {
        setMessageSubmissionFeedback({
          status: "error",
          message: error.message,
          code: error.code,
          statusCode: error.statusCode
        });
        return;
      }

      setMessageSubmissionFeedback({
        status: "error",
        message: "Unable to submit message right now.",
        code: "message_submission_unavailable",
        statusCode: 500
      });
    }
  };

  const submitGroupChatCreateDraft = async () => {
    if (bearerToken === null) {
      setGroupChatCreateFeedback({
        status: "error",
        message: "A stored bearer token is required before creating a group chat.",
        code: "auth_missing",
        statusCode: 401
      });
      return;
    }

    const name = groupChatCreateDraft.name.trim();
    if (name.length === 0) {
      setGroupChatCreateFeedback({
        status: "error",
        message: "Group chat name is required before submitting.",
        code: "invalid_group_chat_draft",
        statusCode: 400
      });
      return;
    }

    if (groupChatCreateDraft.selectedInviteeIds.length === 0) {
      setGroupChatCreateFeedback({
        status: "error",
        message: "Choose at least one visible player before creating a group chat.",
        code: "invalid_group_chat_draft",
        statusCode: 400
      });
      return;
    }

    setGroupChatCreateFeedback({ status: "submitting" });

    try {
      const accepted = await submitGroupChatCreate(
        {
          match_id: envelope.data.match_id,
          tick: envelope.data.state.tick,
          name,
          member_ids: groupChatCreateDraft.selectedInviteeIds
        },
        bearerToken,
        fetch,
        { apiBaseUrl }
      );
      const feedback = describeAcceptedGroupChatCreate(accepted);
      setGroupChatCreateDraft(emptyGroupChatCreateDraft());
      setGroupChatCreateFeedback({
        status: "success",
        message: feedback.message,
        details: feedback.details
      });
    } catch (error: unknown) {
      if (error instanceof GroupChatCreateError) {
        setGroupChatCreateFeedback({
          status: "error",
          message: error.message,
          code: error.code,
          statusCode: error.statusCode
        });
        return;
      }

      setGroupChatCreateFeedback({
        status: "error",
        message: "Unable to create group chat right now.",
        code: "group_chat_create_unavailable",
        statusCode: 500
      });
    }
  };

  const submitTreatyDraft = async () => {
    if (bearerToken === null) {
      setTreatySubmissionFeedback({
        status: "error",
        message: "A stored bearer token is required before submitting diplomacy.",
        code: "auth_missing",
        statusCode: 401
      });
      return;
    }

    if (treatyDraft.counterpartyId.length === 0) {
      setTreatySubmissionFeedback({
        status: "error",
        message: "Choose a visible treaty counterparty before submitting.",
        code: "invalid_treaty_draft",
        statusCode: 400
      });
      return;
    }

    setTreatySubmissionFeedback({ status: "submitting" });

    try {
      const accepted = await submitTreatyAction(
        {
          match_id: envelope.data.match_id,
          counterparty_id: treatyDraft.counterpartyId,
          action: treatyDraft.action,
          treaty_type: treatyDraft.treatyType
        },
        bearerToken,
        fetch,
        { apiBaseUrl }
      );
      const feedback = describeAcceptedTreaty(accepted, envelope.data.player_id);
      setTreatySubmissionFeedback({
        status: "success",
        message: feedback.message,
        details: feedback.details
      });
    } catch (error: unknown) {
      if (error instanceof DiplomacySubmissionError) {
        setTreatySubmissionFeedback({
          status: "error",
          message: error.message,
          code: error.code,
          statusCode: error.statusCode
        });
        return;
      }

      setTreatySubmissionFeedback({
        status: "error",
        message: "Unable to submit diplomacy action right now.",
        code: "diplomacy_submission_unavailable",
        statusCode: 500
      });
    }
  };

  const submitAllianceDraft = async () => {
    if (bearerToken === null) {
      setAllianceSubmissionFeedback({
        status: "error",
        message: "A stored bearer token is required before submitting diplomacy.",
        code: "auth_missing",
        statusCode: 401
      });
      return;
    }

    let request: AllianceActionRequest;
    if (allianceDraft.action === "create") {
      const name = allianceDraft.name.trim();
      if (name.length === 0) {
        setAllianceSubmissionFeedback({
          status: "error",
          message: "Alliance name is required before creating an alliance.",
          code: "invalid_alliance_draft",
          statusCode: 400
        });
        return;
      }
      request = { match_id: envelope.data.match_id, action: "create", name };
    } else if (allianceDraft.action === "join") {
      if (allianceDraft.allianceId.length === 0) {
        setAllianceSubmissionFeedback({
          status: "error",
          message: "Choose a visible alliance before joining.",
          code: "invalid_alliance_draft",
          statusCode: 400
        });
        return;
      }
      request = {
        match_id: envelope.data.match_id,
        action: "join",
        alliance_id: allianceDraft.allianceId
      };
    } else {
      request = { match_id: envelope.data.match_id, action: "leave" };
    }

    setAllianceSubmissionFeedback({ status: "submitting" });

    try {
      const accepted = await submitAllianceAction(request, bearerToken, fetch, { apiBaseUrl });
      const feedback = describeAcceptedAlliance(accepted, allianceDraft.action);
      setAllianceSubmissionFeedback({
        status: "success",
        message: feedback.message,
        details: feedback.details
      });
    } catch (error: unknown) {
      if (error instanceof DiplomacySubmissionError) {
        setAllianceSubmissionFeedback({
          status: "error",
          message: error.message,
          code: error.code,
          statusCode: error.statusCode
        });
        return;
      }

      setAllianceSubmissionFeedback({
        status: "error",
        message: "Unable to submit diplomacy action right now.",
        code: "diplomacy_submission_unavailable",
        statusCode: 500
      });
    }
  };

  return (
    <>
      <section className="panel panel-section">
        <div className="section-heading">
          <h2>Live player state</h2>
          <span className="status-pill">{liveStatus === "live" ? "Live" : "Not live"}</span>
        </div>
        <p>Fog-filtered state plus player-safe diplomacy and chat summaries from the current websocket snapshot.</p>
      </section>

      <MatchLiveMap
        mapLayout={mapLayout}
        liveStatus={liveStatus}
        tick={envelope.data.state.tick}
        perspective="player"
        cities={mapCities}
        armies={mapArmies}
        selectedCityId={selectedCity?.cityId ?? null}
        selectedArmyId={selectedArmy?.armyId ?? null}
        onCitySelect={selectCity}
        onArmySelect={selectArmy}
      />

      <section className="panel panel-section" aria-label="Map selection inspector">
        <h2>Map selection inspector</h2>
        {selectedMapEntity === null ? (
          <p>Select a visible city or army marker to inspect it and use explicit draft helpers.</p>
        ) : selectedCity !== null ? (
          <>
            <p>{`Selected city: ${selectedCity.cityName}`}</p>
            <p>{selectedCity.ownerLabel === null ? "Owner hidden or unknown" : `Owner ${selectedCity.ownerLabel}`}</p>
            <p>{selectedCity.garrisonLabel === null ? "Garrison hidden or unknown" : `Visible garrison ${selectedCity.garrisonLabel}`}</p>
          </>
        ) : selectedArmy !== null ? (
          <>
            <p>{`Selected army: ${selectedArmy.armyId}`}</p>
            <p>{`Owner ${selectedArmy.ownerLabel}`}</p>
            <p>{selectedArmy.troopsLabel === null ? "Visible troops hidden or unknown" : `Visible troops ${selectedArmy.troopsLabel}`}</p>
            <p>
              {selectedArmy.visibleLocationCityId === null
                ? "Visible location hidden or unknown"
                : `Visible location ${formatCityName(selectedArmy.visibleLocationCityId)}`}
            </p>
          </>
        ) : (
          <p>Selected marker is no longer visible in the current snapshot.</p>
        )}
        {selectionGuidance ? <p role="status">{selectionGuidance}</p> : null}
      </section>

      <dl className="panel panel-grid" aria-label="Live player summary">
        <SummaryRow label="Match ID" value={envelope.data.match_id} />
        <SummaryRow label="Viewing player" value={envelope.data.player_id} />
        <SummaryRow label="Tick" value={envelope.data.state.tick} />
        <SummaryRow label="Visible cities" value={Object.keys(envelope.data.state.cities).length} />
        <SummaryRow label="Visible armies" value={envelope.data.state.visible_armies.length} />
        <SummaryRow label="Alliance" value={envelope.data.state.alliance_id ?? "No alliance"} />
      </dl>

      <section className="panel panel-section">
        <h2>Resources</h2>
        <ul className="roster-list" aria-label="Player resources">
          {resourceRows.map((row) => (
            <li key={row.label} className="roster-row">
              <span>{`${row.label} ${row.value(envelope)}`}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="panel panel-section">
        <h2>Fog-filtered movement</h2>
        {envelope.data.state.visible_armies.length === 0 ? (
          <p>No player-safe army movement is visible in this update.</p>
        ) : (
          <ul className="roster-list" aria-label="Visible player armies">
            {envelope.data.state.visible_armies.map((army) => {
              const mapArmy = mapArmies.find((entry) => entry.armyId === army.id) ?? null;
              const transitText =
                mapArmy === null ? null : describeTransitListText(mapArmy, cityNamesById);

              return (
                <li key={army.id} className="roster-row">
                  <span>{transitText ?? describeArmy(army)}</span>
                </li>
              );
            })}
          </ul>
        )}
        {partialArmy ? <p>{`Visible enemy army near ${partialArmy.destination ?? partialArmy.location ?? "the frontier"}`}</p> : null}
      </section>

      <section className="panel panel-section">
        <h2>Chat and diplomacy</h2>
        <ul className="roster-list" aria-label="Player chat and diplomacy summaries">
          <li className="roster-row">
            <span>{latestWorldMessage ? latestWorldMessage.content : "No world message yet."}</span>
          </li>
          <li className="roster-row">
            <span>{latestDirectMessage ? latestDirectMessage.content : "No direct message yet."}</span>
          </li>
          <li className="roster-row">
            <span>{describeGroupChat(latestGroupChat, latestGroupMessage)}</span>
          </li>
          <li className="roster-row">
            <span>{describeTreaty(latestTreaty)}</span>
          </li>
          <li className="roster-row">
            <span>{describeAlliance(latestAlliance)}</span>
          </li>
        </ul>
      </section>

      <section className="panel panel-section">
        <h2>Live messaging</h2>
        <p>Submit world, direct, or group messages for the current websocket tick. The live timeline stays read-only.</p>

        <section aria-label="Create group chat">
          <h3>Create group chat</h3>
          <p>Use the current websocket snapshot to choose visible players, then wait for the next snapshot to show the chat in the live list.</p>

          {groupChatCreateFeedback.status === "success" ? (
            <div role="status">
              <p>{groupChatCreateFeedback.message}</p>
              {groupChatCreateFeedback.details?.map((detail) => <p key={detail}>{detail}</p>)}
            </div>
          ) : null}

          {groupChatCreateFeedback.status === "error" ? (
            <div role="alert">
              <p>{groupChatCreateFeedback.message}</p>
              <p>{`Error code: ${groupChatCreateFeedback.code}`}</p>
              <p>{`HTTP status: ${groupChatCreateFeedback.statusCode}`}</p>
            </div>
          ) : null}

          <label>
            Group chat name
            <input
              type="text"
              value={groupChatCreateDraft.name}
              onChange={(event) => updateGroupChatCreateDraft({ name: event.target.value })}
            />
          </label>

          {visiblePlayerIds.length === 0 ? (
            <p>No other visible players can be invited from the current snapshot.</p>
          ) : (
            <fieldset>
              <legend>Invite players</legend>
              {visiblePlayerIds.map((playerId) => {
                const isChecked = groupChatCreateDraft.selectedInviteeIds.includes(playerId);

                return (
                  <label key={playerId}>
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={(event) => {
                        const nextSelectedInviteeIds = event.target.checked
                          ? [...groupChatCreateDraft.selectedInviteeIds, playerId]
                          : groupChatCreateDraft.selectedInviteeIds.filter(
                              (selectedPlayerId) => selectedPlayerId !== playerId
                            );

                        updateGroupChatCreateDraft({
                          selectedInviteeIds: nextSelectedInviteeIds
                        });
                      }}
                    />
                    {playerId}
                  </label>
                );
              })}
            </fieldset>
          )}

          <button
            className="button-link"
            type="button"
            onClick={() => void submitGroupChatCreateDraft()}
            disabled={!canSubmitGroupChatCreate}
          >
            {groupChatCreateFeedback.status === "submitting" ? "Submitting…" : "Create group chat"}
          </button>
        </section>

        {messageSubmissionFeedback.status === "success" ? (
          <p role="status">{messageSubmissionFeedback.message}</p>
        ) : null}

        {messageSubmissionFeedback.status === "error" ? (
          <div role="alert">
            <p>{messageSubmissionFeedback.message}</p>
            <p>{`Error code: ${messageSubmissionFeedback.code}`}</p>
            <p>{`HTTP status: ${messageSubmissionFeedback.statusCode}`}</p>
          </div>
        ) : null}

        <label>
          Channel
          <select
            value={messageDraft.channel}
            onChange={(event) =>
              updateMessageDraft({ channel: event.target.value as LiveMessagingChannel })
            }
          >
            <option value="world">world</option>
            <option value="direct">direct</option>
            <option value="group">group</option>
          </select>
        </label>

        {messageDraft.channel === "direct" ? (
          <label>
            Direct target
            <select
              value={messageDraft.directRecipientId}
              onChange={(event) => updateMessageDraft({ directRecipientId: event.target.value })}
            >
              {directTargetIds.length === 0 ? <option value="">No visible players</option> : null}
              {directTargetIds.map((playerId) => (
                <option key={playerId} value={playerId}>
                  {playerId}
                </option>
              ))}
            </select>
          </label>
        ) : null}

        {messageDraft.channel === "group" ? (
          <label>
            Group chat
            <select
              value={messageDraft.groupChatId}
              onChange={(event) => updateMessageDraft({ groupChatId: event.target.value })}
            >
              {visibleGroupChats.length === 0 ? <option value="">No visible group chats</option> : null}
              {visibleGroupChats.map((groupChat) => (
                <option key={groupChat.group_chat_id} value={groupChat.group_chat_id}>
                  {groupChat.name}
                </option>
              ))}
            </select>
          </label>
        ) : null}

        <label>
          Message content
          <textarea
            value={messageDraft.content}
            onChange={(event) => updateMessageDraft({ content: event.target.value })}
          />
        </label>

        <button className="button-link" type="button" onClick={() => void submitMessageDraft()} disabled={!canSubmitMessage}>
          {messageSubmissionFeedback.status === "submitting" ? "Submitting…" : "Submit message"}
        </button>
      </section>

      <section className="panel panel-section">
        <h2>Live diplomacy</h2>
        <p>Submit treaty and alliance actions through the shipped routes. The websocket snapshot stays authoritative.</p>

        {treatySubmissionFeedback.status === "success" ? (
          <div role="status">
            <p>{treatySubmissionFeedback.message}</p>
            {treatySubmissionFeedback.details?.map((detail) => <p key={detail}>{detail}</p>)}
          </div>
        ) : null}

        {treatySubmissionFeedback.status === "error" ? (
          <div role="alert">
            <p>{treatySubmissionFeedback.message}</p>
            <p>{`Error code: ${treatySubmissionFeedback.code}`}</p>
            <p>{`HTTP status: ${treatySubmissionFeedback.statusCode}`}</p>
          </div>
        ) : null}

        <label>
          Treaty action
          <select
            value={treatyDraft.action}
            onChange={(event) => updateTreatyDraft({ action: event.target.value as TreatyAction })}
          >
            <option value="propose">propose</option>
            <option value="accept">accept</option>
            <option value="withdraw">withdraw</option>
          </select>
        </label>

        <label>
          Treaty type
          <select
            value={treatyDraft.treatyType}
            onChange={(event) => updateTreatyDraft({ treatyType: event.target.value as TreatyType })}
          >
            <option value="non_aggression">non_aggression</option>
            <option value="defensive">defensive</option>
            <option value="trade">trade</option>
          </select>
        </label>

        <label>
          Treaty counterparty
          <select
            value={treatyDraft.counterpartyId}
            onChange={(event) => updateTreatyDraft({ counterpartyId: event.target.value })}
          >
            {treatyCounterpartyIds.length === 0 ? <option value="">No visible players</option> : null}
            {treatyCounterpartyIds.map((playerId) => (
              <option key={playerId} value={playerId}>
                {playerId}
              </option>
            ))}
          </select>
        </label>

        <button className="button-link secondary" type="button" onClick={applyTreatyCounterpartySelection}>
          Use selected marker for treaty counterparty
        </button>

        {allianceSubmissionFeedback.status === "success" ? (
          <div role="status">
            <p>{allianceSubmissionFeedback.message}</p>
            {allianceSubmissionFeedback.details?.map((detail) => <p key={detail}>{detail}</p>)}
          </div>
        ) : null}

        {allianceSubmissionFeedback.status === "error" ? (
          <div role="alert">
            <p>{allianceSubmissionFeedback.message}</p>
            <p>{`Error code: ${allianceSubmissionFeedback.code}`}</p>
            <p>{`HTTP status: ${allianceSubmissionFeedback.statusCode}`}</p>
          </div>
        ) : null}

        <button className="button-link" type="button" onClick={() => void submitTreatyDraft()} disabled={!canSubmitTreaty}>
          {treatySubmissionFeedback.status === "submitting" ? "Submitting…" : "Submit treaty"}
        </button>

        <p>{`Current alliance: ${envelope.data.state.alliance_id ?? "none"}`}</p>

        <label>
          Alliance action
          <select
            value={allianceDraft.action}
            onChange={(event) => updateAllianceDraft({ action: event.target.value as AllianceAction })}
          >
            <option value="create">create</option>
            <option value="join">join</option>
            <option value="leave">leave</option>
          </select>
        </label>

        {allianceDraft.action === "create" ? (
          <label>
            Alliance name
            <input
              type="text"
              value={allianceDraft.name}
              onChange={(event) => updateAllianceDraft({ name: event.target.value })}
            />
          </label>
        ) : null}

        {allianceDraft.action === "join" ? (
          <label>
            Join alliance
            <select
              value={allianceDraft.allianceId}
              onChange={(event) => updateAllianceDraft({ allianceId: event.target.value })}
            >
              {joinableAlliances.length === 0 ? <option value="">No joinable alliances</option> : null}
              {joinableAlliances.map((alliance) => (
                <option key={alliance.alliance_id} value={alliance.alliance_id}>
                  {alliance.alliance_id}
                </option>
              ))}
            </select>
          </label>
        ) : null}

        <button className="button-link" type="button" onClick={() => void submitAllianceDraft()} disabled={!canSubmitAlliance}>
          {allianceSubmissionFeedback.status === "submitting" ? "Submitting…" : "Submit alliance"}
        </button>
      </section>

      <section className="panel panel-section">
        <h2>Order Drafts</h2>
        <p>Draft text-first orders for the current live tick. Submission only confirms what the server accepted.</p>

        {submissionFeedback.status === "success" ? <p role="status">{submissionFeedback.message}</p> : null}

        {submissionFeedback.status === "error" ? (
          <div role="alert">
            <p>{submissionFeedback.message}</p>
            <p>{`Error code: ${submissionFeedback.code}`}</p>
            <p>{`HTTP status: ${submissionFeedback.statusCode}`}</p>
          </div>
        ) : null}

        <section aria-label="Movement drafts">
          <h3>Movement</h3>
          <button className="button-link secondary" type="button" onClick={addMovementDraft}>
            Add movement order
          </button>
          {drafts.movements.length === 0 ? <p>No movement orders drafted.</p> : null}
          {drafts.movements.map((draft, index) => (
            <div key={`movement-${index}`}>
              <label>
                {`Movement army ID ${index + 1}`}
                <input
                  type="text"
                  value={draft.armyId}
                  onChange={(event) => updateMovementDraft(index, "armyId", event.target.value)}
                />
              </label>
              <label>
                {`Movement destination ${index + 1}`}
                <input
                  type="text"
                  value={draft.destination}
                  onChange={(event) => updateMovementDraft(index, "destination", event.target.value)}
                />
              </label>
              <button
                className="button-link secondary"
                type="button"
                onClick={() => removeMovementDraft(index)}
              >
                {`Remove movement order ${index + 1}`}
              </button>
              <button className="button-link secondary" type="button" onClick={() => applyMovementArmySelection(index)}>
                {`Use selected army for movement army ID ${index + 1}`}
              </button>
              <button className="button-link secondary" type="button" onClick={() => applyMovementDestinationSelection(index)}>
                {`Use selected marker for movement destination ${index + 1}`}
              </button>
            </div>
          ))}
        </section>

        <section aria-label="Recruitment drafts">
          <h3>Recruitment</h3>
          <button className="button-link secondary" type="button" onClick={addRecruitmentDraft}>
            Add recruitment order
          </button>
          {drafts.recruitment.length === 0 ? <p>No recruitment orders drafted.</p> : null}
          {drafts.recruitment.map((draft, index) => (
            <div key={`recruitment-${index}`}>
              <label>
                {`Recruitment city ${index + 1}`}
                <input
                  type="text"
                  value={draft.city}
                  onChange={(event) => updateRecruitmentDraft(index, "city", event.target.value)}
                />
              </label>
              <label>
                {`Recruitment troops ${index + 1}`}
                <input
                  type="number"
                  value={draft.troops}
                  onChange={(event) => updateRecruitmentDraft(index, "troops", event.target.value)}
                />
              </label>
              <button
                className="button-link secondary"
                type="button"
                onClick={() => removeRecruitmentDraft(index)}
              >
                {`Remove recruitment order ${index + 1}`}
              </button>
              <button className="button-link secondary" type="button" onClick={() => applyRecruitmentCitySelection(index)}>
                {`Use selected city for recruitment city ${index + 1}`}
              </button>
            </div>
          ))}
        </section>

        <section aria-label="Upgrade drafts">
          <h3>Upgrade</h3>
          <button className="button-link secondary" type="button" onClick={addUpgradeDraft}>
            Add upgrade order
          </button>
          {drafts.upgrades.length === 0 ? <p>No upgrade orders drafted.</p> : null}
          {drafts.upgrades.map((draft, index) => (
            <div key={`upgrade-${index}`}>
              <label>
                {`Upgrade city ${index + 1}`}
                <input
                  type="text"
                  value={draft.city}
                  onChange={(event) => updateUpgradeDraft(index, "city", event.target.value)}
                />
              </label>
              <label>
                {`Upgrade track ${index + 1}`}
                <select
                  value={draft.track}
                  onChange={(event) => updateUpgradeDraft(index, "track", event.target.value)}
                >
                  <option value="economy">economy</option>
                  <option value="military">military</option>
                  <option value="fortification">fortification</option>
                </select>
              </label>
              <label>
                {`Upgrade target tier ${index + 1}`}
                <input
                  type="number"
                  value={draft.targetTier}
                  onChange={(event) => updateUpgradeDraft(index, "targetTier", event.target.value)}
                />
              </label>
              <button
                className="button-link secondary"
                type="button"
                onClick={() => removeUpgradeDraft(index)}
              >
                {`Remove upgrade order ${index + 1}`}
              </button>
              <button className="button-link secondary" type="button" onClick={() => applyUpgradeCitySelection(index)}>
                {`Use selected city for upgrade city ${index + 1}`}
              </button>
            </div>
          ))}
        </section>

        <section aria-label="Transfer drafts">
          <h3>Transfer</h3>
          <button className="button-link secondary" type="button" onClick={addTransferDraft}>
            Add transfer order
          </button>
          {drafts.transfers.length === 0 ? <p>No transfer orders drafted.</p> : null}
          {drafts.transfers.map((draft, index) => (
            <div key={`transfer-${index}`}>
              <label>
                {`Transfer destination ${index + 1}`}
                <input
                  type="text"
                  value={draft.to}
                  onChange={(event) => updateTransferDraft(index, "to", event.target.value)}
                />
              </label>
              <label>
                {`Transfer resource ${index + 1}`}
                <select
                  value={draft.resource}
                  onChange={(event) => updateTransferDraft(index, "resource", event.target.value)}
                >
                  <option value="food">food</option>
                  <option value="production">production</option>
                  <option value="money">money</option>
                </select>
              </label>
              <label>
                {`Transfer amount ${index + 1}`}
                <input
                  type="number"
                  value={draft.amount}
                  onChange={(event) => updateTransferDraft(index, "amount", event.target.value)}
                />
              </label>
              <button
                className="button-link secondary"
                type="button"
                onClick={() => removeTransferDraft(index)}
              >
                {`Remove transfer order ${index + 1}`}
              </button>
              <button className="button-link secondary" type="button" onClick={() => applyTransferDestinationSelection(index)}>
                {`Use selected marker for transfer destination ${index + 1}`}
              </button>
            </div>
          ))}
        </section>

        <button className="button-link" type="button" onClick={() => void submitDrafts()} disabled={!canSubmit}>
          {submissionFeedback.status === "submitting" ? "Submitting…" : "Submit drafted orders"}
        </button>
      </section>
    </>
  );
}

function SummaryRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metadata-row">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function describeArmy(army: VisibleArmyState): string {
  const location = army.location ?? army.destination ?? "in transit";
  const troops = typeof army.troops === "number" ? `${army.troops} troops` : "unknown strength";
  return `${army.owner} at ${location} with ${troops} (${army.visibility})`;
}

function describeGroupChat(
  groupChat: GroupChatRecord | null,
  groupMessage: GroupMessageRecord | null
): string {
  if (!groupChat) {
    return "No alliance or group chat summary yet.";
  }

  if (!groupMessage || groupMessage.group_chat_id !== groupChat.group_chat_id) {
    return groupChat.name;
  }

  return `${groupChat.name}: ${groupMessage.content}`;
}

function describeTreaty(treaty: TreatyRecord | null): string {
  if (!treaty) {
    return "No treaty summary yet.";
  }

  return `${treaty.treaty_type} ${treaty.status} between ${treaty.player_a_id} and ${treaty.player_b_id}`;
}

function describeAlliance(alliance: AllianceRecord | null): string {
  if (!alliance) {
    return "No alliance summary yet.";
  }

  return `Alliance ${alliance.name} led by ${alliance.leader_id}`;
}
