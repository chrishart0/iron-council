"use client";

import { useEffect, useState } from "react";
import {
  CommandSubmissionError,
  GuidedAgentControlsError,
  DiplomacySubmissionError,
  GroupChatCreateError,
  MessageSubmissionError,
  submitOwnedAgentGuidance,
  submitOwnedAgentOverride,
  submitAllianceAction,
  submitGroupChatCreate,
  submitGroupChatMessage,
  submitMatchMessage,
  submitMatchOrders,
  submitTreatyAction
} from "../../../lib/api";
import type {
  AllianceAction,
  AllianceRecord,
  AllianceActionAcceptanceResponse,
  AllianceActionRequest,
  GroupChatCreateAcceptanceResponse,
  GroupChatMessageAcceptanceResponse,
  GroupChatRecord,
  MessageAcceptanceResponse,
  MatchOrdersCommandRequest,
  PlayerMatchEnvelope,
  TreatyActionAcceptanceResponse,
  VisibleArmyState
} from "../../../lib/types";
import type { BritainMapLayout } from "../../../lib/britain-map";
import {
  MatchLiveMap,
  type MatchLiveMapArmyDatum,
  type MatchLiveMapCityDatum
} from "../match-live-map";
import { HumanLiveDiplomacyPanel } from "./human-live-diplomacy-panel";
import { HumanLiveMessagingPanel } from "./human-live-messaging-panel";
import { HumanLiveOrdersPanel } from "./human-live-orders-panel";
import { HumanLiveGuidedPanel } from "./human-live-guided-panel";
import { HumanMatchLiveSelectionPanel } from "./human-match-live-selection-panel";
import { HumanMatchLiveSummaryPanels } from "./human-match-live-summary-panels";
import type {
  AllianceDraftState,
  AsyncSubmissionFeedback,
  GuidedSessionState,
  GroupChatCreateDraftState,
  LiveMessagingChannel,
  MapSelection,
  MessageDraftState,
  MovementDraft,
  OrderDraftState,
  RecruitmentDraft,
  SubmissionFeedback,
  TransferDraft,
  TreatyDraftState,
  UpgradeDraft
} from "./human-match-live-types";

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
  liveStatus,
  guidedState,
  refreshGuidedSession
}: {
  envelope: PlayerMatchEnvelope;
  mapLayout: BritainMapLayout;
  apiBaseUrl: string;
  bearerToken: string | null;
  liveStatus: "live" | "not_live";
  guidedState: GuidedSessionState;
  refreshGuidedSession: () => void;
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
  const [guidanceDraft, setGuidanceDraft] = useState("");
  const [guidanceFeedback, setGuidanceFeedback] = useState<AsyncSubmissionFeedback>({
    status: "idle"
  });
  const [guidedOverrideFeedback, setGuidedOverrideFeedback] = useState<AsyncSubmissionFeedback>({
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
  const canSubmitGuidance =
    liveStatus === "live" &&
    bearerToken !== null &&
    guidedState.status === "ready" &&
    guidanceFeedback.status !== "submitting" &&
    guidanceDraft.trim().length > 0;
  const canSubmitGuidedOverride =
    liveStatus === "live" &&
    bearerToken !== null &&
    guidedState.status === "ready" &&
    guidedOverrideFeedback.status !== "submitting";

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

  const updateGuidanceDraft = (value: string) => {
    setGuidanceFeedback({ status: "idle" });
    setGuidanceDraft(value);
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

  const submitGuidanceDraft = async () => {
    if (bearerToken === null) {
      setGuidanceFeedback({
        status: "error",
        message: "A stored bearer token is required before sending guidance.",
        code: "auth_missing",
        statusCode: 401
      });
      return;
    }

    if (guidedState.status !== "ready") {
      setGuidanceFeedback({
        status: "error",
        message: "Guided controls are not ready yet.",
        code: "guided_controls_unavailable",
        statusCode: 409
      });
      return;
    }

    const content = guidanceDraft.trim();
    if (content.length === 0) {
      setGuidanceFeedback({
        status: "error",
        message: "Guidance message is required before submitting.",
        code: "invalid_guidance_draft",
        statusCode: 400
      });
      return;
    }

    setGuidanceFeedback({ status: "submitting" });

    try {
      const accepted = await submitOwnedAgentGuidance(
        {
          match_id: envelope.data.match_id,
          tick: envelope.data.state.tick,
          content
        },
        guidedState.agentId,
        bearerToken,
        fetch,
        { apiBaseUrl }
      );

      setGuidanceDraft("");
      setGuidanceFeedback({
        status: "success",
        message: `Guidance accepted for tick ${accepted.tick}.`
      });
      refreshGuidedSession();
    } catch (error: unknown) {
      if (error instanceof GuidedAgentControlsError) {
        setGuidanceFeedback({
          status: "error",
          message: error.message,
          code: error.code,
          statusCode: error.statusCode
        });
        return;
      }

      setGuidanceFeedback({
        status: "error",
        message: "Unable to load guided agent controls right now.",
        code: "guided_agent_controls_unavailable",
        statusCode: 500
      });
    }
  };

  const submitGuidedOverrideDraft = async () => {
    if (bearerToken === null) {
      setGuidedOverrideFeedback({
        status: "error",
        message: "A stored bearer token is required before submitting a guided override.",
        code: "auth_missing",
        statusCode: 401
      });
      return;
    }

    if (guidedState.status !== "ready") {
      setGuidedOverrideFeedback({
        status: "error",
        message: "Guided controls are not ready yet.",
        code: "guided_controls_unavailable",
        statusCode: 409
      });
      return;
    }

    const nextRequest = buildOrderRequest(envelope, drafts);
    if (!nextRequest.ok) {
      setGuidedOverrideFeedback({
        status: "error",
        message: nextRequest.message,
        code: "invalid_order_draft",
        statusCode: 400
      });
      return;
    }

    setGuidedOverrideFeedback({ status: "submitting" });

    try {
      const accepted = await submitOwnedAgentOverride(
        nextRequest.request,
        guidedState.agentId,
        bearerToken,
        fetch,
        { apiBaseUrl }
      );

      setGuidedOverrideFeedback({
        status: "success",
        message: `Guided override accepted for tick ${accepted.tick}.`
      });
      refreshGuidedSession();
    } catch (error: unknown) {
      if (error instanceof GuidedAgentControlsError) {
        setGuidedOverrideFeedback({
          status: "error",
          message: error.message,
          code: error.code,
          statusCode: error.statusCode
        });
        return;
      }

      setGuidedOverrideFeedback({
        status: "error",
        message: "Unable to load guided agent controls right now.",
        code: "guided_agent_controls_unavailable",
        statusCode: 500
      });
    }
  };

  return (
    <>
      <HumanMatchLiveSummaryPanels
        envelope={envelope}
        liveStatus={liveStatus}
        mapArmies={mapArmies}
        cityNamesById={cityNamesById}
        latestWorldMessage={latestWorldMessage}
        latestDirectMessage={latestDirectMessage}
        latestGroupChat={latestGroupChat}
        latestGroupMessage={latestGroupMessage}
        latestTreaty={latestTreaty}
        latestAlliance={latestAlliance}
        partialArmy={partialArmy}
      />

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

      <HumanMatchLiveSelectionPanel
        selectedMapEntity={selectedMapEntity}
        selectedCity={selectedCity}
        selectedArmy={selectedArmy}
        selectionGuidance={selectionGuidance}
      />

      <HumanLiveGuidedPanel
        guidedState={guidedState}
        guidanceDraft={guidanceDraft}
        guidanceFeedback={guidanceFeedback}
        guidedOverrideFeedback={guidedOverrideFeedback}
        canSubmitGuidance={canSubmitGuidance}
        canSubmitGuidedOverride={canSubmitGuidedOverride}
        updateGuidanceDraft={updateGuidanceDraft}
        submitGuidanceDraft={submitGuidanceDraft}
        submitGuidedOverrideDraft={submitGuidedOverrideDraft}
      />

      <HumanLiveMessagingPanel
        visiblePlayerIds={visiblePlayerIds}
        visibleGroupChats={visibleGroupChats}
        groupChatCreateDraft={groupChatCreateDraft}
        groupChatCreateFeedback={groupChatCreateFeedback}
        messageDraft={messageDraft}
        messageSubmissionFeedback={messageSubmissionFeedback}
        canSubmitGroupChatCreate={canSubmitGroupChatCreate}
        canSubmitMessage={canSubmitMessage}
        updateGroupChatCreateDraft={updateGroupChatCreateDraft}
        updateMessageDraft={updateMessageDraft}
        submitGroupChatCreateDraft={submitGroupChatCreateDraft}
        submitMessageDraft={submitMessageDraft}
      />

      <HumanLiveDiplomacyPanel
        currentAllianceId={envelope.data.state.alliance_id}
        treatyCounterpartyIds={treatyCounterpartyIds}
        joinableAlliances={joinableAlliances}
        treatyDraft={treatyDraft}
        treatySubmissionFeedback={treatySubmissionFeedback}
        allianceDraft={allianceDraft}
        allianceSubmissionFeedback={allianceSubmissionFeedback}
        canSubmitTreaty={canSubmitTreaty}
        canSubmitAlliance={canSubmitAlliance}
        updateTreatyDraft={updateTreatyDraft}
        updateAllianceDraft={updateAllianceDraft}
        applyTreatyCounterpartySelection={applyTreatyCounterpartySelection}
        submitTreatyDraft={submitTreatyDraft}
        submitAllianceDraft={submitAllianceDraft}
      />

      <HumanLiveOrdersPanel
        drafts={drafts}
        submissionFeedback={submissionFeedback}
        canSubmit={canSubmit}
        addMovementDraft={addMovementDraft}
        addRecruitmentDraft={addRecruitmentDraft}
        addUpgradeDraft={addUpgradeDraft}
        addTransferDraft={addTransferDraft}
        updateMovementDraft={updateMovementDraft}
        updateRecruitmentDraft={updateRecruitmentDraft}
        updateUpgradeDraft={updateUpgradeDraft}
        updateTransferDraft={updateTransferDraft}
        removeMovementDraft={removeMovementDraft}
        removeRecruitmentDraft={removeRecruitmentDraft}
        removeUpgradeDraft={removeUpgradeDraft}
        removeTransferDraft={removeTransferDraft}
        applyMovementArmySelection={applyMovementArmySelection}
        applyMovementDestinationSelection={applyMovementDestinationSelection}
        applyRecruitmentCitySelection={applyRecruitmentCitySelection}
        applyUpgradeCitySelection={applyUpgradeCitySelection}
        applyTransferDestinationSelection={applyTransferDestinationSelection}
        submitDrafts={submitDrafts}
      />
    </>
  );
}
