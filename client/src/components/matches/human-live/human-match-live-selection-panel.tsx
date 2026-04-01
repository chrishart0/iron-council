import type { MatchLiveMapArmyDatum, MatchLiveMapCityDatum } from "../match-live-map";
import type { MapSelection } from "./human-match-live-types";

type HumanMatchLiveSelectionPanelProps = {
  selectedMapEntity: MapSelection | null;
  selectedCity: MatchLiveMapCityDatum | null;
  selectedArmy: MatchLiveMapArmyDatum | null;
  selectionGuidance: string | null;
};

function formatCityName(cityId: string) {
  return cityId.charAt(0).toUpperCase() + cityId.slice(1);
}

export function HumanMatchLiveSelectionPanel({
  selectedMapEntity,
  selectedCity,
  selectedArmy,
  selectionGuidance
}: HumanMatchLiveSelectionPanelProps) {
  return (
    <section className="panel panel-section" aria-label="Map selection inspector">
      <h2>Map selection inspector</h2>
      {selectedMapEntity === null ? (
        <p>Select a visible city or army marker to inspect it and use explicit draft helpers.</p>
      ) : selectedCity !== null ? (
        <>
          <p>{`Selected city: ${selectedCity.cityName}`}</p>
          <p>{selectedCity.ownerLabel === null ? "Owner hidden or unknown" : `Owner ${selectedCity.ownerLabel}`}</p>
          <p>
            {selectedCity.garrisonLabel === null
              ? "Garrison hidden or unknown"
              : `Visible garrison ${selectedCity.garrisonLabel}`}
          </p>
        </>
      ) : selectedArmy !== null ? (
        <>
          <p>{`Selected army: ${selectedArmy.armyId}`}</p>
          <p>{`Owner ${selectedArmy.ownerLabel}`}</p>
          <p>
            {selectedArmy.troopsLabel === null
              ? "Visible troops hidden or unknown"
              : `Visible troops ${selectedArmy.troopsLabel}`}
          </p>
          <p>
            {selectedArmy.visibleLocationCityId === null
              ? "Visible location hidden or unknown"
              : `Visible location ${formatCityName(selectedArmy.visibleLocationCityId)}`}
          </p>
        </>
      ) : (
        <p>Selected marker is no longer visible in the current snapshot.</p>
      )}
      {selectionGuidance ? <p role="status">{selectionGuidance}</p> : null}
    </section>
  );
}
