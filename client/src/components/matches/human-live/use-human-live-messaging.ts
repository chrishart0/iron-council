"use client";

import { useEffect, useState } from "react";
import {
  GroupChatCreateError,
  MessageSubmissionError,
  submitGroupChatCreate,
  submitGroupChatMessage,
  submitMatchMessage
} from "../../../lib/api";
import type { GroupChatRecord, PlayerMatchEnvelope } from "../../../lib/types";
import type {
  AsyncSubmissionFeedback,
  GroupChatCreateDraftState,
  MessageDraftState
} from "./human-match-live-types";
import {
  describeAcceptedGroupChatCreate,
  describeAcceptedMessage,
  emptyGroupChatCreateDraft,
  emptyMessageDraft
} from "./human-match-live-snapshot-support";

type UseHumanLiveMessagingArgs = {
  envelope: PlayerMatchEnvelope;
  apiBaseUrl: string;
  bearerToken: string | null;
  liveStatus: "live" | "not_live";
  visiblePlayerIds: string[];
  visibleGroupChats: GroupChatRecord[];
};

export function useHumanLiveMessaging({
  envelope,
  apiBaseUrl,
  bearerToken,
  liveStatus,
  visiblePlayerIds,
  visibleGroupChats
}: UseHumanLiveMessagingArgs) {
  const [messageDraft, setMessageDraft] = useState<MessageDraftState>(() =>
    emptyMessageDraft(visiblePlayerIds, visibleGroupChats)
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

  useEffect(() => {
    setMessageDraft((currentDraft) => {
      const nextChannel =
        currentDraft.channel === "direct" && visiblePlayerIds.length === 0
          ? "world"
          : currentDraft.channel === "group" && visibleGroupChats.length === 0
            ? "world"
            : currentDraft.channel;
      const nextDirectRecipientId = visiblePlayerIds.includes(currentDraft.directRecipientId)
        ? currentDraft.directRecipientId
        : (visiblePlayerIds[0] ?? "");
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
  }, [visibleGroupChats, visiblePlayerIds]);

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

  const canSubmitMessage =
    liveStatus === "live" && bearerToken !== null && messageSubmissionFeedback.status !== "submitting";
  const canSubmitGroupChatCreate =
    liveStatus === "live" &&
    bearerToken !== null &&
    groupChatCreateFeedback.status !== "submitting" &&
    groupChatCreateDraft.name.trim().length > 0 &&
    groupChatCreateDraft.selectedInviteeIds.length > 0 &&
    visiblePlayerIds.length > 0;

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

  return {
    messageDraft,
    messageSubmissionFeedback,
    groupChatCreateDraft,
    groupChatCreateFeedback,
    canSubmitMessage,
    canSubmitGroupChatCreate,
    updateMessageDraft,
    updateGroupChatCreateDraft,
    submitMessageDraft,
    submitGroupChatCreateDraft
  };
}
