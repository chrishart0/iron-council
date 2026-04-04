"use client";

import type { PlayerMatchEnvelope } from "../../../lib/types";
import type { BritainMapLayout } from "../../../lib/britain-map";
import { MatchLiveMap } from "../match-live-map";
import { HumanLiveDiplomacyPanel } from "./human-live-diplomacy-panel";
import { HumanLiveGuidedPanel } from "./human-live-guided-panel";
import { HumanLiveMessagingPanel } from "./human-live-messaging-panel";
import { HumanLiveOrdersPanel } from "./human-live-orders-panel";
import { HumanMatchLiveSelectionPanel } from "./human-match-live-selection-panel";
import { HumanMatchLiveSummaryPanels } from "./human-match-live-summary-panels";
import {
  buildHumanLiveSnapshotViewModel,
  collectJoinableAlliances,
  collectVisiblePlayerIds
} from "./human-match-live-snapshot-support";
import type { GuidedSessionState } from "./human-match-live-types";
import { useHumanLiveDiplomacy } from "./use-human-live-diplomacy";
import { useHumanLiveGuidedControls } from "./use-human-live-guided-controls";
import { useHumanLiveMapSelection } from "./use-human-live-map-selection";
import { useHumanLiveMessaging } from "./use-human-live-messaging";
import { useHumanLiveOrders } from "./use-human-live-orders";

type HumanMatchLiveSnapshotProps = {
  envelope: PlayerMatchEnvelope;
  mapLayout: BritainMapLayout;
  apiBaseUrl: string;
  bearerToken: string | null;
  liveStatus: "live" | "not_live";
  guidedState: GuidedSessionState;
  refreshGuidedSession: () => void;
};

export function HumanMatchLiveSnapshot({
  envelope,
  mapLayout,
  apiBaseUrl,
  bearerToken,
  liveStatus,
  guidedState,
  refreshGuidedSession
}: HumanMatchLiveSnapshotProps) {
  const visiblePlayerIds = collectVisiblePlayerIds(envelope);
  const visibleGroupChats = envelope.data.group_chats;
  const treatyCounterpartyIds = visiblePlayerIds;
  const joinableAlliances = collectJoinableAlliances(envelope);
  const {
    latestWorldMessage,
    latestDirectMessage,
    latestGroupChat,
    latestGroupMessage,
    latestTreaty,
    latestAlliance,
    partialArmy,
    mapCities,
    mapArmies,
    cityNamesById
  } = buildHumanLiveSnapshotViewModel(envelope, mapLayout);
  const {
    selectedMapEntity,
    selectionGuidance,
    setSelectionGuidance,
    selectedCity,
    selectedArmy,
    selectedCounterpartyId,
    selectCity,
    selectArmy
  } = useHumanLiveMapSelection({
    currentPlayerId: envelope.data.player_id,
    mapCities,
    mapArmies
  });
  const orders = useHumanLiveOrders({
    envelope,
    apiBaseUrl,
    bearerToken,
    liveStatus,
    clearSelectionGuidance: () => setSelectionGuidance(null)
  });
  const messaging = useHumanLiveMessaging({
    envelope,
    apiBaseUrl,
    bearerToken,
    liveStatus,
    visiblePlayerIds,
    visibleGroupChats
  });
  const diplomacy = useHumanLiveDiplomacy({
    envelope,
    apiBaseUrl,
    bearerToken,
    liveStatus,
    treatyCounterpartyIds,
    joinableAlliances
  });
  const guidedControls = useHumanLiveGuidedControls({
    envelope,
    drafts: orders.drafts,
    apiBaseUrl,
    bearerToken,
    liveStatus,
    guidedState,
    refreshGuidedSession
  });

  const setSelectionMessage = (message: string) => {
    orders.resetSubmissionFeedback();
    setSelectionGuidance(message);
  };

  const applyMovementArmySelection = (index: number) => {
    if (selectedArmy === null) {
      setSelectionMessage(
        `Selection helper could not update movement army ID ${index + 1}: select a visible army first.`
      );
      return;
    }

    orders.updateMovementDraft(index, "armyId", selectedArmy.armyId);
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

    orders.updateMovementDraft(index, "destination", destination);
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

    orders.updateRecruitmentDraft(index, "city", selectedCity.cityId);
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

    orders.updateUpgradeDraft(index, "city", selectedCity.cityId);
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

    orders.updateTransferDraft(index, "to", selectedCounterpartyId);
    setSelectionGuidance(`Selection helper set transfer destination ${index + 1} to ${selectedCounterpartyId}.`);
  };

  const applyTreatyCounterpartySelection = () => {
    if (selectedCounterpartyId === null) {
      setSelectionMessage(
        "Selection helper could not update treaty counterparty: the selected marker does not expose a visible counterparty."
      );
      return;
    }

    diplomacy.updateTreatyDraft({ counterpartyId: selectedCounterpartyId });
    setSelectionGuidance(`Selection helper set treaty counterparty to ${selectedCounterpartyId}.`);
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
        guidanceDraft={guidedControls.guidanceDraft}
        guidanceFeedback={guidedControls.guidanceFeedback}
        guidedOverrideFeedback={guidedControls.guidedOverrideFeedback}
        canSubmitGuidance={guidedControls.canSubmitGuidance}
        canSubmitGuidedOverride={guidedControls.canSubmitGuidedOverride}
        updateGuidanceDraft={guidedControls.updateGuidanceDraft}
        submitGuidanceDraft={guidedControls.submitGuidanceDraft}
        submitGuidedOverrideDraft={guidedControls.submitGuidedOverrideDraft}
      />

      <HumanLiveMessagingPanel
        visiblePlayerIds={visiblePlayerIds}
        visibleGroupChats={visibleGroupChats}
        groupChatCreateDraft={messaging.groupChatCreateDraft}
        groupChatCreateFeedback={messaging.groupChatCreateFeedback}
        messageDraft={messaging.messageDraft}
        messageSubmissionFeedback={messaging.messageSubmissionFeedback}
        canSubmitGroupChatCreate={messaging.canSubmitGroupChatCreate}
        canSubmitMessage={messaging.canSubmitMessage}
        updateGroupChatCreateDraft={messaging.updateGroupChatCreateDraft}
        updateMessageDraft={messaging.updateMessageDraft}
        submitGroupChatCreateDraft={messaging.submitGroupChatCreateDraft}
        submitMessageDraft={messaging.submitMessageDraft}
      />

      <HumanLiveDiplomacyPanel
        currentAllianceId={envelope.data.state.alliance_id}
        treatyCounterpartyIds={treatyCounterpartyIds}
        joinableAlliances={joinableAlliances}
        treatyDraft={diplomacy.treatyDraft}
        treatySubmissionFeedback={diplomacy.treatySubmissionFeedback}
        allianceDraft={diplomacy.allianceDraft}
        allianceSubmissionFeedback={diplomacy.allianceSubmissionFeedback}
        canSubmitTreaty={diplomacy.canSubmitTreaty}
        canSubmitAlliance={diplomacy.canSubmitAlliance}
        updateTreatyDraft={diplomacy.updateTreatyDraft}
        updateAllianceDraft={diplomacy.updateAllianceDraft}
        applyTreatyCounterpartySelection={applyTreatyCounterpartySelection}
        submitTreatyDraft={diplomacy.submitTreatyDraft}
        submitAllianceDraft={diplomacy.submitAllianceDraft}
      />

      <HumanLiveOrdersPanel
        drafts={orders.drafts}
        submissionFeedback={orders.submissionFeedback}
        canSubmit={orders.canSubmit}
        addMovementDraft={orders.addMovementDraft}
        addRecruitmentDraft={orders.addRecruitmentDraft}
        addUpgradeDraft={orders.addUpgradeDraft}
        addTransferDraft={orders.addTransferDraft}
        updateMovementDraft={orders.updateMovementDraft}
        updateRecruitmentDraft={orders.updateRecruitmentDraft}
        updateUpgradeDraft={orders.updateUpgradeDraft}
        updateTransferDraft={orders.updateTransferDraft}
        removeMovementDraft={orders.removeMovementDraft}
        removeRecruitmentDraft={orders.removeRecruitmentDraft}
        removeUpgradeDraft={orders.removeUpgradeDraft}
        removeTransferDraft={orders.removeTransferDraft}
        applyMovementArmySelection={applyMovementArmySelection}
        applyMovementDestinationSelection={applyMovementDestinationSelection}
        applyRecruitmentCitySelection={applyRecruitmentCitySelection}
        applyUpgradeCitySelection={applyUpgradeCitySelection}
        applyTransferDestinationSelection={applyTransferDestinationSelection}
        submitDrafts={orders.submitDrafts}
      />
    </>
  );
}
