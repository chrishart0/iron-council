import type { AsyncSubmissionFeedback, GuidedSessionState } from "./human-match-live-types";

type HumanLiveGuidedPanelProps = {
  guidedState: GuidedSessionState;
  guidanceDraft: string;
  guidanceFeedback: AsyncSubmissionFeedback;
  guidedOverrideFeedback: AsyncSubmissionFeedback;
  canSubmitGuidance: boolean;
  canSubmitGuidedOverride: boolean;
  updateGuidanceDraft: (value: string) => void;
  submitGuidanceDraft: () => Promise<void>;
  submitGuidedOverrideDraft: () => Promise<void>;
};

function summarizeQueuedOrders(guidedState: GuidedSessionState): string[] {
  if (guidedState.status !== "ready") {
    return [];
  }

  const { queued_orders: queuedOrders } = guidedState.guidedSession;
  return [
    ...queuedOrders.movements.map((movement) => `${movement.army_id} -> ${movement.destination}`),
    ...queuedOrders.recruitment.map((recruitment) => `${recruitment.city} recruits ${recruitment.troops}`),
    ...queuedOrders.upgrades.map(
      (upgrade) => `${upgrade.city} ${upgrade.track} -> tier ${upgrade.target_tier}`
    ),
    ...queuedOrders.transfers.map(
      (transfer) => `${transfer.to} receives ${transfer.amount} ${transfer.resource}`
    )
  ];
}

function renderFeedback(feedback: AsyncSubmissionFeedback) {
  if (feedback.status === "success") {
    return (
      <div aria-live="polite">
        <p>{feedback.message}</p>
        {feedback.details?.map((detail) => <p key={detail}>{detail}</p>)}
      </div>
    );
  }

  if (feedback.status === "error") {
    return (
      <div role="alert">
        <p>{feedback.message}</p>
        <p>{`Error code: ${feedback.code}`}</p>
        <p>{`HTTP status: ${feedback.statusCode}`}</p>
      </div>
    );
  }

  return null;
}

export function HumanLiveGuidedPanel({
  guidedState,
  guidanceDraft,
  guidanceFeedback,
  guidedOverrideFeedback,
  canSubmitGuidance,
  canSubmitGuidedOverride,
  updateGuidanceDraft,
  submitGuidanceDraft,
  submitGuidedOverrideDraft
}: HumanLiveGuidedPanelProps) {
  if (guidedState.agentId === null) {
    return null;
  }

  const queuedOrderSummaries = summarizeQueuedOrders(guidedState);

  return (
    <section className="panel panel-section">
      <h2>Guided agent controls</h2>
      <p>Private owner guidance and current-tick overrides for the authenticated guided agent.</p>

      {guidedState.status === "loading" ? <p aria-live="polite">Loading guided-session context.</p> : null}

      {guidedState.status === "error" ? (
        <div role="alert">
          <p>{guidedState.errorMessage}</p>
          <p>{`Guided agent: ${guidedState.agentId}`}</p>
        </div>
      ) : null}

      {guidedState.status === "ready" ? (
        <>
          <p>{`Guided agent: ${guidedState.guidedSession.agent_id}`}</p>

          <section aria-label="Queued guided orders">
            <h3>Queued orders</h3>
            {queuedOrderSummaries.length === 0 ? (
              <p>No queued orders for the current tick.</p>
            ) : (
              <ul className="roster-list">
                {queuedOrderSummaries.map((summary) => (
                  <li key={summary} className="roster-row">
                    <span>{summary}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section aria-label="Private guidance history">
            <h3>Private guidance history</h3>
            {guidedState.guidedSession.guidance.length === 0 ? (
              <p>No private guidance recorded.</p>
            ) : (
              <ul className="roster-list">
                {guidedState.guidedSession.guidance.map((guidance) => (
                  <li key={guidance.guidance_id} className="roster-row">
                    <span>{guidance.content}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section aria-label="Guidance composer">
            <h3>Send private guidance</h3>
            {renderFeedback(guidanceFeedback)}
            <label>
              Guidance message
              <textarea
                value={guidanceDraft}
                onChange={(event) => updateGuidanceDraft(event.target.value)}
              />
            </label>
            <button
              className="button-link"
              type="button"
              onClick={() => void submitGuidanceDraft()}
              disabled={!canSubmitGuidance}
            >
              {guidanceFeedback.status === "submitting" ? "Submitting…" : "Send guidance"}
            </button>
          </section>

          <section aria-label="Guided override controls">
            <h3>Guided override</h3>
            <p>Submit the current order drafts as the authoritative next-tick guided override.</p>
            {renderFeedback(guidedOverrideFeedback)}
            <button
              className="button-link"
              type="button"
              onClick={() => void submitGuidedOverrideDraft()}
              disabled={!canSubmitGuidedOverride}
            >
              {guidedOverrideFeedback.status === "submitting" ? "Submitting…" : "Submit guided override"}
            </button>
          </section>
        </>
      ) : null}
    </section>
  );
}
