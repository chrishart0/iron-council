"use client";

import { useEffect, useMemo, useState } from "react";
import type { MatchLiveMapArmyDatum, MatchLiveMapCityDatum } from "../match-live-map";
import type { MapSelection } from "./human-match-live-types";
import { getSelectionOwnerCounterparty } from "./human-match-live-snapshot-support";

type UseHumanLiveMapSelectionArgs = {
  currentPlayerId: string;
  mapCities: MatchLiveMapCityDatum[];
  mapArmies: MatchLiveMapArmyDatum[];
};

export function useHumanLiveMapSelection({
  currentPlayerId,
  mapCities,
  mapArmies
}: UseHumanLiveMapSelectionArgs) {
  const [selectedMapEntity, setSelectedMapEntity] = useState<MapSelection | null>(null);
  const [selectionGuidance, setSelectionGuidance] = useState<string | null>(null);

  useEffect(() => {
    if (selectedMapEntity === null) {
      return;
    }

    if (
      selectedMapEntity.kind === "city" &&
      mapCities.some((city) => city.cityId === selectedMapEntity.cityId)
    ) {
      return;
    }

    if (
      selectedMapEntity.kind === "army" &&
      mapArmies.some((army) => army.armyId === selectedMapEntity.armyId)
    ) {
      return;
    }

    setSelectedMapEntity(null);
    setSelectionGuidance("The previous map selection is no longer visible in the current snapshot.");
  }, [mapArmies, mapCities, selectedMapEntity]);

  const selectedCity = useMemo(
    () =>
      selectedMapEntity?.kind === "city"
        ? mapCities.find((city) => city.cityId === selectedMapEntity.cityId) ?? null
        : null,
    [mapCities, selectedMapEntity]
  );
  const selectedArmy = useMemo(
    () =>
      selectedMapEntity?.kind === "army"
        ? mapArmies.find((army) => army.armyId === selectedMapEntity.armyId) ?? null
        : null,
    [mapArmies, selectedMapEntity]
  );
  const selectedCounterpartyId = useMemo(
    () =>
      getSelectionOwnerCounterparty(
        selectedMapEntity,
        currentPlayerId,
        selectedCity,
        selectedArmy
      ),
    [currentPlayerId, selectedArmy, selectedCity, selectedMapEntity]
  );

  const selectCity = (city: MatchLiveMapCityDatum) => {
    setSelectedMapEntity({ kind: "city", cityId: city.cityId });
    setSelectionGuidance(null);
  };

  const selectArmy = (army: MatchLiveMapArmyDatum) => {
    setSelectedMapEntity({ kind: "army", armyId: army.armyId });
    setSelectionGuidance(null);
  };

  return {
    selectedMapEntity,
    selectionGuidance,
    setSelectionGuidance,
    selectedCity,
    selectedArmy,
    selectedCounterpartyId,
    selectCity,
    selectArmy
  };
}
