import type { AllianceRecord } from "../../../lib/types";
import type {
  AllianceDraftState,
  AsyncSubmissionFeedback,
  TreatyDraftState
} from "./human-match-live-types";

type HumanLiveDiplomacyPanelProps = {
  currentAllianceId: string | null;
  treatyCounterpartyIds: string[];
  joinableAlliances: AllianceRecord[];
  treatyDraft: TreatyDraftState;
  treatySubmissionFeedback: AsyncSubmissionFeedback;
  allianceDraft: AllianceDraftState;
  allianceSubmissionFeedback: AsyncSubmissionFeedback;
  canSubmitTreaty: boolean;
  canSubmitAlliance: boolean;
  updateTreatyDraft: (updates: Partial<TreatyDraftState>) => void;
  updateAllianceDraft: (updates: Partial<AllianceDraftState>) => void;
  applyTreatyCounterpartySelection: () => void;
  submitTreatyDraft: () => Promise<void>;
  submitAllianceDraft: () => Promise<void>;
};

export function HumanLiveDiplomacyPanel({
  currentAllianceId,
  treatyCounterpartyIds,
  joinableAlliances,
  treatyDraft,
  treatySubmissionFeedback,
  allianceDraft,
  allianceSubmissionFeedback,
  canSubmitTreaty,
  canSubmitAlliance,
  updateTreatyDraft,
  updateAllianceDraft,
  applyTreatyCounterpartySelection,
  submitTreatyDraft,
  submitAllianceDraft
}: HumanLiveDiplomacyPanelProps) {
  return (
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
        <select value={treatyDraft.action} onChange={(event) => updateTreatyDraft({ action: event.target.value as TreatyDraftState["action"] })}>
          <option value="propose">propose</option>
          <option value="accept">accept</option>
          <option value="withdraw">withdraw</option>
        </select>
      </label>

      <label>
        Treaty type
        <select
          value={treatyDraft.treatyType}
          onChange={(event) => updateTreatyDraft({ treatyType: event.target.value as TreatyDraftState["treatyType"] })}
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

      <p>{`Current alliance: ${currentAllianceId ?? "none"}`}</p>

      <label>
        Alliance action
        <select
          value={allianceDraft.action}
          onChange={(event) => updateAllianceDraft({ action: event.target.value as AllianceDraftState["action"] })}
        >
          <option value="create">create</option>
          <option value="join">join</option>
          <option value="leave">leave</option>
        </select>
      </label>

      {allianceDraft.action === "create" ? (
        <label>
          Alliance name
          <input type="text" value={allianceDraft.name} onChange={(event) => updateAllianceDraft({ name: event.target.value })} />
        </label>
      ) : null}

      {allianceDraft.action === "join" ? (
        <label>
          Join alliance
          <select value={allianceDraft.allianceId} onChange={(event) => updateAllianceDraft({ allianceId: event.target.value })}>
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
  );
}
