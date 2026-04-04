"use client";

import { useState } from "react";
import {
  GuidedAgentControlsError,
  submitOwnedAgentGuidance,
  submitOwnedAgentOverride
} from "../../../lib/api";
import type { PlayerMatchEnvelope } from "../../../lib/types";
import type {
  AsyncSubmissionFeedback,
  GuidedSessionState,
  OrderDraftState
} from "./human-match-live-types";
import { buildOrderRequest } from "./human-match-live-snapshot-support";

type UseHumanLiveGuidedControlsArgs = {
  envelope: PlayerMatchEnvelope;
  drafts: OrderDraftState;
  apiBaseUrl: string;
  bearerToken: string | null;
  liveStatus: "live" | "not_live";
  guidedState: GuidedSessionState;
  refreshGuidedSession: () => void;
};

export function useHumanLiveGuidedControls({
  envelope,
  drafts,
  apiBaseUrl,
  bearerToken,
  liveStatus,
  guidedState,
  refreshGuidedSession
}: UseHumanLiveGuidedControlsArgs) {
  const [guidanceDraft, setGuidanceDraft] = useState("");
  const [guidanceFeedback, setGuidanceFeedback] = useState<AsyncSubmissionFeedback>({
    status: "idle"
  });
  const [guidedOverrideFeedback, setGuidedOverrideFeedback] = useState<AsyncSubmissionFeedback>({
    status: "idle"
  });

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

  const updateGuidanceDraft = (value: string) => {
    setGuidanceFeedback({ status: "idle" });
    setGuidanceDraft(value);
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

  return {
    guidanceDraft,
    guidanceFeedback,
    guidedOverrideFeedback,
    canSubmitGuidance,
    canSubmitGuidedOverride,
    updateGuidanceDraft,
    submitGuidanceDraft,
    submitGuidedOverrideDraft
  };
}
