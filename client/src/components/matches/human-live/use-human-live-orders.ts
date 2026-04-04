"use client";

import { useState } from "react";
import { CommandSubmissionError, submitMatchOrders } from "../../../lib/api";
import type { PlayerMatchEnvelope } from "../../../lib/types";
import type {
  OrderDraftState,
  RecruitmentDraft,
  SubmissionFeedback,
  TransferDraft,
  UpgradeDraft
} from "./human-match-live-types";
import {
  buildOrderRequest,
  emptyDraftState,
  emptyMovementDraft,
  emptyRecruitmentDraft,
  emptyTransferDraft,
  emptyUpgradeDraft
} from "./human-match-live-snapshot-support";

type UseHumanLiveOrdersArgs = {
  envelope: PlayerMatchEnvelope;
  apiBaseUrl: string;
  bearerToken: string | null;
  liveStatus: "live" | "not_live";
  clearSelectionGuidance: () => void;
};

export function useHumanLiveOrders({
  envelope,
  apiBaseUrl,
  bearerToken,
  liveStatus,
  clearSelectionGuidance
}: UseHumanLiveOrdersArgs) {
  const [drafts, setDrafts] = useState<OrderDraftState>(() => emptyDraftState());
  const [submissionFeedback, setSubmissionFeedback] = useState<SubmissionFeedback>({
    status: "idle"
  });

  const canSubmit = liveStatus === "live" && bearerToken !== null && submissionFeedback.status !== "submitting";

  const resetSubmissionFeedback = () => {
    setSubmissionFeedback({ status: "idle" });
  };

  const updateMovementDraft = (index: number, key: "armyId" | "destination", value: string) => {
    clearSelectionGuidance();
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      movements: currentDrafts.movements.map((draft, draftIndex) =>
        draftIndex === index ? { ...draft, [key]: value } : draft
      )
    }));
  };

  const updateRecruitmentDraft = (index: number, key: keyof RecruitmentDraft, value: string) => {
    clearSelectionGuidance();
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      recruitment: currentDrafts.recruitment.map((draft, draftIndex) =>
        draftIndex === index ? { ...draft, [key]: value } : draft
      )
    }));
  };

  const updateUpgradeDraft = (index: number, key: keyof UpgradeDraft, value: string) => {
    clearSelectionGuidance();
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      upgrades: currentDrafts.upgrades.map((draft, draftIndex) =>
        draftIndex === index ? { ...draft, [key]: value } : draft
      )
    }));
  };

  const updateTransferDraft = (index: number, key: keyof TransferDraft, value: string) => {
    clearSelectionGuidance();
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      transfers: currentDrafts.transfers.map((draft, draftIndex) =>
        draftIndex === index ? { ...draft, [key]: value } : draft
      )
    }));
  };

  const addMovementDraft = () => {
    resetSubmissionFeedback();
    clearSelectionGuidance();
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      movements: [...currentDrafts.movements, emptyMovementDraft()]
    }));
  };

  const addRecruitmentDraft = () => {
    resetSubmissionFeedback();
    clearSelectionGuidance();
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      recruitment: [...currentDrafts.recruitment, emptyRecruitmentDraft()]
    }));
  };

  const addUpgradeDraft = () => {
    resetSubmissionFeedback();
    clearSelectionGuidance();
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      upgrades: [...currentDrafts.upgrades, emptyUpgradeDraft()]
    }));
  };

  const addTransferDraft = () => {
    resetSubmissionFeedback();
    clearSelectionGuidance();
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      transfers: [...currentDrafts.transfers, emptyTransferDraft()]
    }));
  };

  const removeMovementDraft = (index: number) => {
    resetSubmissionFeedback();
    clearSelectionGuidance();
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      movements: currentDrafts.movements.filter((_, draftIndex) => draftIndex !== index)
    }));
  };

  const removeRecruitmentDraft = (index: number) => {
    resetSubmissionFeedback();
    clearSelectionGuidance();
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      recruitment: currentDrafts.recruitment.filter((_, draftIndex) => draftIndex !== index)
    }));
  };

  const removeUpgradeDraft = (index: number) => {
    resetSubmissionFeedback();
    clearSelectionGuidance();
    setDrafts((currentDrafts) => ({
      ...currentDrafts,
      upgrades: currentDrafts.upgrades.filter((_, draftIndex) => draftIndex !== index)
    }));
  };

  const removeTransferDraft = (index: number) => {
    resetSubmissionFeedback();
    clearSelectionGuidance();
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

  return {
    drafts,
    submissionFeedback,
    canSubmit,
    resetSubmissionFeedback,
    setSubmissionFeedback,
    updateMovementDraft,
    updateRecruitmentDraft,
    updateUpgradeDraft,
    updateTransferDraft,
    addMovementDraft,
    addRecruitmentDraft,
    addUpgradeDraft,
    addTransferDraft,
    removeMovementDraft,
    removeRecruitmentDraft,
    removeUpgradeDraft,
    removeTransferDraft,
    submitDrafts
  };
}
