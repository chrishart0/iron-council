"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  buildPlayerMatchWebSocketUrl,
  CommandSubmissionError,
  DiplomacySubmissionError,
  MessageSubmissionError,
  fetchPublicMatchDetail,
  getPlayerWebSocketCloseMessage,
  parsePlayerMatchEnvelope,
  parseWebSocketApiErrorEnvelope,
  PublicMatchDetailError,
  submitAllianceAction,
  submitGroupChatMessage,
  submitMatchMessage,
  submitMatchOrders,
  submitTreatyAction
} from "../../lib/api";
import type {
  AllianceRecord,
  AllianceAction,
  AllianceActionAcceptanceResponse,
  AllianceActionRequest,
  GroupChatRecord,
  GroupChatMessageAcceptanceResponse,
  GroupMessageRecord,
  MessageAcceptanceResponse,
  MatchOrdersCommandRequest,
  PlayerMatchEnvelope,
  PublicMatchDetailResponse,
  ResourceType,
  TreatyAction,
  TreatyActionAcceptanceResponse,
  TreatyRecord,
  TreatyType,
  UpgradeTrack,
  VisibleArmyState
} from "../../lib/types";
import { useSession } from "../session/session-provider";

type HumanMatchLivePageProps = {
  matchId: string;
};

type MatchDetailState =
  | {
      status: "loading";
      match: null;
      errorMessage: null;
    }
  | {
      status: "ready";
      match: PublicMatchDetailResponse;
      errorMessage: null;
    }
  | {
      status: "error";
      match: null;
      errorMessage: string;
    };

type LiveConnectionState =
  | {
      status: "idle" | "connecting";
      envelope: null;
      message: string | null;
    }
  | {
      status: "live";
      envelope: PlayerMatchEnvelope;
      message: string | null;
    }
  | {
      status: "not_live";
      envelope: PlayerMatchEnvelope | null;
      message: string;
    };

const resourceRows: Array<{
  label: string;
  value: (envelope: PlayerMatchEnvelope) => number | string;
}> = [
  { label: "Food", value: (envelope) => envelope.data.state.resources.food },
  { label: "Production", value: (envelope) => envelope.data.state.resources.production },
  { label: "Money", value: (envelope) => envelope.data.state.resources.money }
];

export function HumanMatchLivePage({ matchId }: HumanMatchLivePageProps) {
  const { apiBaseUrl, bearerToken, hasHydrated } = useSession();
  const [matchState, setMatchState] = useState<MatchDetailState>({
    status: "loading",
    match: null,
    errorMessage: null
  });
  const [liveState, setLiveState] = useState<LiveConnectionState>({
    status: "idle",
    envelope: null,
    message: null
  });

  useEffect(() => {
    if (!hasHydrated) {
      return;
    }

    if (!bearerToken) {
      setMatchState({
        status: "error",
        match: null,
        errorMessage: "This live player page requires a stored human bearer token before it can connect."
      });
      setLiveState({
        status: "not_live",
        envelope: null,
        message: "This live player page requires a stored human bearer token before it can connect."
      });
      return;
    }

    let isActive = true;

    setMatchState({
      status: "loading",
      match: null,
      errorMessage: null
    });
    setLiveState({
      status: "idle",
      envelope: null,
      message: null
    });

    void fetchPublicMatchDetail(matchId, fetch, { apiBaseUrl })
      .then((match) => {
        if (!isActive) {
          return;
        }

        setMatchState({
          status: "ready",
          match,
          errorMessage: null
        });
      })
      .catch((error: unknown) => {
        if (!isActive) {
          return;
        }

        const errorMessage =
          error instanceof PublicMatchDetailError
            ? error.message
            : "Unable to load this public match right now.";

        setMatchState({
          status: "error",
          match: null,
          errorMessage
        });
        setLiveState({
          status: "not_live",
          envelope: null,
          message: errorMessage
        });
      });

    return () => {
      isActive = false;
    };
  }, [apiBaseUrl, bearerToken, hasHydrated, matchId]);

  useEffect(() => {
    if (!hasHydrated || !bearerToken || matchState.status !== "ready") {
      return;
    }

    if (matchState.match.status !== "active") {
      setLiveState({
        status: "not_live",
        envelope: null,
        message: `This match is ${matchState.match.status}, so the authenticated live page is not active.`
      });
      return;
    }

    const socket = new WebSocket(buildPlayerMatchWebSocketUrl(matchId, bearerToken, { apiBaseUrl }));
    let hasClosed = false;

    setLiveState({
      status: "connecting",
      envelope: null,
      message: null
    });

    const markUnavailable = (options?: { message?: string | null; reason?: string }) => {
      if (hasClosed) {
        return;
      }

      hasClosed = true;

      setLiveState((currentState) => ({
        status: "not_live",
        envelope: currentState.envelope,
        message:
          options?.message ??
          getPlayerWebSocketCloseMessage(options?.reason ?? "") ??
          (currentState.envelope === null
            ? "Live updates are unavailable right now."
            : "Showing the last confirmed player snapshot. Reconnect to resume live updates.")
      }));
    };

    socket.onmessage = (event) => {
      try {
        const parsedPayload: unknown = JSON.parse(event.data);
        const errorEnvelope = parseWebSocketApiErrorEnvelope(parsedPayload);

        if (errorEnvelope !== null) {
          markUnavailable({ message: errorEnvelope.error.message });
          return;
        }

        const payload = parsePlayerMatchEnvelope(parsedPayload);

        setLiveState({
          status: "live",
          envelope: payload,
          message: null
        });
      } catch {
        markUnavailable();
      }
    };

    socket.onerror = () => {
      markUnavailable();
    };

    socket.onclose = (event) => {
      markUnavailable({ reason: event.reason });
    };

    return () => {
      hasClosed = true;
      socket.close();
    };
  }, [apiBaseUrl, bearerToken, hasHydrated, matchId, matchState]);

  const statusPanel =
    matchState.status === "loading" ? (
      <section className="panel state-card" aria-live="polite" aria-busy="true">
        <strong>Loading live match access</strong>
        <p>Waiting for the public match summary before opening the player websocket.</p>
      </section>
    ) : liveState.status === "connecting" ? (
      <section className="panel state-card" aria-live="polite">
        <strong>Connecting player feed</strong>
        <p>Opening the authenticated websocket now.</p>
      </section>
    ) : liveState.status === "not_live" ? (
      <section className="panel state-card" role="status">
        <strong>{liveState.envelope === null ? "Live updates unavailable" : "Live connection lost"}</strong>
        <p>{liveState.message}</p>
      </section>
    ) : null;

  return (
    <>
      <section className="hero">
        <h2>{`Live Match ${matchId}`}</h2>
        <p>Authenticated player-safe updates over the shipped match websocket contract.</p>
        <div className="actions">
          <Link className="button-link secondary" href={`/matches/${matchId}`}>
            Back to match detail
          </Link>
        </div>
      </section>

      {statusPanel}

      {liveState.envelope !== null ? (
        <HumanMatchLiveSnapshot
          envelope={liveState.envelope}
          apiBaseUrl={apiBaseUrl}
          bearerToken={bearerToken}
          liveStatus={liveState.status === "live" ? "live" : "not_live"}
        />
      ) : null}
    </>
  );
}

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

function collectJoinableAlliances(envelope: PlayerMatchEnvelope): AllianceRecord[] {
  return envelope.data.alliances.filter(
    (alliance) => !alliance.members.some((member) => member.player_id === envelope.data.player_id)
  );
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

function HumanMatchLiveSnapshot({
  envelope,
  apiBaseUrl,
  bearerToken,
  liveStatus
}: {
  envelope: PlayerMatchEnvelope;
  apiBaseUrl: string;
  bearerToken: string | null;
  liveStatus: "live" | "not_live";
}) {
  const [drafts, setDrafts] = useState<OrderDraftState>(() => emptyDraftState());
  const [submissionFeedback, setSubmissionFeedback] = useState<SubmissionFeedback>({
    status: "idle"
  });
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
  const canSubmit = liveStatus === "live" && bearerToken !== null && submissionFeedback.status !== "submitting";
  const canSubmitMessage =
    liveStatus === "live" && bearerToken !== null && messageSubmissionFeedback.status !== "submitting";
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

  const updateMovementDraft = (index: number, key: keyof MovementDraft, value: string) => {
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      movements: currentDrafts.movements.map((draft, draftIndex) =>
        draftIndex === index ? { ...draft, [key]: value } : draft
      )
    }));
  };

  const updateRecruitmentDraft = (index: number, key: keyof RecruitmentDraft, value: string) => {
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      recruitment: currentDrafts.recruitment.map((draft, draftIndex) =>
        draftIndex === index ? { ...draft, [key]: value } : draft
      )
    }));
  };

  const updateUpgradeDraft = (index: number, key: keyof UpgradeDraft, value: string) => {
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      upgrades: currentDrafts.upgrades.map((draft, draftIndex) =>
        draftIndex === index ? { ...draft, [key]: value } : draft
      )
    }));
  };

  const updateTransferDraft = (index: number, key: keyof TransferDraft, value: string) => {
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      transfers: currentDrafts.transfers.map((draft, draftIndex) =>
        draftIndex === index ? { ...draft, [key]: value } : draft
      )
    }));
  };

  const addMovementDraft = () => {
    setSubmissionFeedback({ status: "idle" });
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      movements: [...currentDrafts.movements, emptyMovementDraft()]
    }));
  };

  const addRecruitmentDraft = () => {
    setSubmissionFeedback({ status: "idle" });
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      recruitment: [...currentDrafts.recruitment, emptyRecruitmentDraft()]
    }));
  };

  const addUpgradeDraft = () => {
    setSubmissionFeedback({ status: "idle" });
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      upgrades: [...currentDrafts.upgrades, emptyUpgradeDraft()]
    }));
  };

  const addTransferDraft = () => {
    setSubmissionFeedback({ status: "idle" });
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      transfers: [...currentDrafts.transfers, emptyTransferDraft()]
    }));
  };

  const removeMovementDraft = (index: number) => {
    setSubmissionFeedback({ status: "idle" });
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      movements: currentDrafts.movements.filter((_, draftIndex) => draftIndex !== index)
    }));
  };

  const removeRecruitmentDraft = (index: number) => {
    setSubmissionFeedback({ status: "idle" });
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      recruitment: currentDrafts.recruitment.filter((_, draftIndex) => draftIndex !== index)
    }));
  };

  const removeUpgradeDraft = (index: number) => {
    setSubmissionFeedback({ status: "idle" });
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      upgrades: currentDrafts.upgrades.filter((_, draftIndex) => draftIndex !== index)
    }));
  };

  const removeTransferDraft = (index: number) => {
    setSubmissionFeedback({ status: "idle" });
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
            {envelope.data.state.visible_armies.map((army) => (
              <li key={army.id} className="roster-row">
                <span>{describeArmy(army)}</span>
              </li>
            ))}
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
