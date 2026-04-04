"use client";

import { useEffect, useState } from "react";
import { DiplomacySubmissionError, submitAllianceAction, submitTreatyAction } from "../../../lib/api";
import type { AllianceRecord, PlayerMatchEnvelope } from "../../../lib/types";
import type {
  AllianceDraftState,
  AsyncSubmissionFeedback,
  TreatyDraftState
} from "./human-match-live-types";
import {
  buildAllianceActionRequest,
  describeAcceptedAlliance,
  describeAcceptedTreaty,
  emptyAllianceDraft,
  emptyTreatyDraft
} from "./human-match-live-snapshot-support";

type UseHumanLiveDiplomacyArgs = {
  envelope: PlayerMatchEnvelope;
  apiBaseUrl: string;
  bearerToken: string | null;
  liveStatus: "live" | "not_live";
  treatyCounterpartyIds: string[];
  joinableAlliances: AllianceRecord[];
};

export function useHumanLiveDiplomacy({
  envelope,
  apiBaseUrl,
  bearerToken,
  liveStatus,
  treatyCounterpartyIds,
  joinableAlliances
}: UseHumanLiveDiplomacyArgs) {
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

  const canSubmitTreaty =
    liveStatus === "live" && bearerToken !== null && treatySubmissionFeedback.status !== "submitting";
  const canSubmitAlliance =
    liveStatus === "live" && bearerToken !== null && allianceSubmissionFeedback.status !== "submitting";

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

    const nextRequest = buildAllianceActionRequest(envelope, allianceDraft);
    if (!nextRequest.ok) {
      setAllianceSubmissionFeedback({
        status: "error",
        message: nextRequest.message,
        code: "invalid_alliance_draft",
        statusCode: 400
      });
      return;
    }

    setAllianceSubmissionFeedback({ status: "submitting" });

    try {
      const accepted = await submitAllianceAction(nextRequest.request, bearerToken, fetch, { apiBaseUrl });
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

  return {
    treatyDraft,
    treatySubmissionFeedback,
    allianceDraft,
    allianceSubmissionFeedback,
    canSubmitTreaty,
    canSubmitAlliance,
    updateTreatyDraft,
    updateAllianceDraft,
    submitTreatyDraft,
    submitAllianceDraft
  };
}
