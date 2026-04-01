import type { ResourceType, UpgradeTrack } from "../../../lib/types";
import type {
  OrderDraftState,
  SubmissionFeedback
} from "./human-match-live-types";

type HumanLiveOrdersPanelProps = {
  drafts: OrderDraftState;
  submissionFeedback: SubmissionFeedback;
  canSubmit: boolean;
  addMovementDraft: () => void;
  addRecruitmentDraft: () => void;
  addUpgradeDraft: () => void;
  addTransferDraft: () => void;
  updateMovementDraft: (index: number, key: "armyId" | "destination", value: string) => void;
  updateRecruitmentDraft: (index: number, key: "city" | "troops", value: string) => void;
  updateUpgradeDraft: (index: number, key: "city" | "track" | "targetTier", value: string) => void;
  updateTransferDraft: (index: number, key: "to" | "resource" | "amount", value: string) => void;
  removeMovementDraft: (index: number) => void;
  removeRecruitmentDraft: (index: number) => void;
  removeUpgradeDraft: (index: number) => void;
  removeTransferDraft: (index: number) => void;
  applyMovementArmySelection: (index: number) => void;
  applyMovementDestinationSelection: (index: number) => void;
  applyRecruitmentCitySelection: (index: number) => void;
  applyUpgradeCitySelection: (index: number) => void;
  applyTransferDestinationSelection: (index: number) => void;
  submitDrafts: () => Promise<void>;
};

export function HumanLiveOrdersPanel({
  drafts,
  submissionFeedback,
  canSubmit,
  addMovementDraft,
  addRecruitmentDraft,
  addUpgradeDraft,
  addTransferDraft,
  updateMovementDraft,
  updateRecruitmentDraft,
  updateUpgradeDraft,
  updateTransferDraft,
  removeMovementDraft,
  removeRecruitmentDraft,
  removeUpgradeDraft,
  removeTransferDraft,
  applyMovementArmySelection,
  applyMovementDestinationSelection,
  applyRecruitmentCitySelection,
  applyUpgradeCitySelection,
  applyTransferDestinationSelection,
  submitDrafts
}: HumanLiveOrdersPanelProps) {
  return (
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
              <input type="text" value={draft.armyId} onChange={(event) => updateMovementDraft(index, "armyId", event.target.value)} />
            </label>
            <label>
              {`Movement destination ${index + 1}`}
              <input
                type="text"
                value={draft.destination}
                onChange={(event) => updateMovementDraft(index, "destination", event.target.value)}
              />
            </label>
            <button className="button-link secondary" type="button" onClick={() => removeMovementDraft(index)}>
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
              <input type="text" value={draft.city} onChange={(event) => updateRecruitmentDraft(index, "city", event.target.value)} />
            </label>
            <label>
              {`Recruitment troops ${index + 1}`}
              <input
                type="number"
                value={draft.troops}
                onChange={(event) => updateRecruitmentDraft(index, "troops", event.target.value)}
              />
            </label>
            <button className="button-link secondary" type="button" onClick={() => removeRecruitmentDraft(index)}>
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
              <input type="text" value={draft.city} onChange={(event) => updateUpgradeDraft(index, "city", event.target.value)} />
            </label>
            <label>
              {`Upgrade track ${index + 1}`}
              <select
                value={draft.track}
                onChange={(event) => updateUpgradeDraft(index, "track", event.target.value as UpgradeTrack)}
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
            <button className="button-link secondary" type="button" onClick={() => removeUpgradeDraft(index)}>
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
              <input type="text" value={draft.to} onChange={(event) => updateTransferDraft(index, "to", event.target.value)} />
            </label>
            <label>
              {`Transfer resource ${index + 1}`}
              <select
                value={draft.resource}
                onChange={(event) => updateTransferDraft(index, "resource", event.target.value as ResourceType)}
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
            <button className="button-link secondary" type="button" onClick={() => removeTransferDraft(index)}>
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
  );
}
