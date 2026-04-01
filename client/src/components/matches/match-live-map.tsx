import type { KeyboardEvent } from "react";
import { type BritainMapLayout } from "../../lib/britain-map";

export type MatchLiveMapCityDatum = {
  cityId: string;
  cityName: string;
  ownerLabel: string | null;
  ownerVisibility: "full" | "partial";
  garrisonLabel: string | null;
};

export type MatchLiveMapArmyDatum = {
  armyId: string;
  cityId: string;
  cityName: string;
  ownerLabel: string;
  troopsLabel: string | null;
  visibility: "full" | "partial";
  visibleLocationCityId: string | null;
  transit: MatchLiveMapTransitDatum;
};

export type MatchLiveMapTransitDatum = {
  status: "stationary" | "in_transit";
  ticksRemaining: number;
  destinationCityId: string | null;
  pathCityIds: string[] | null;
};

type MatchLiveMapProps = {
  mapLayout: BritainMapLayout;
  liveStatus: "live" | "not_live";
  tick: number | null;
  perspective: "spectator" | "player";
  cities: MatchLiveMapCityDatum[];
  armies: MatchLiveMapArmyDatum[];
  selectedCityId?: string | null;
  selectedArmyId?: string | null;
  onCitySelect?: ((city: MatchLiveMapCityDatum) => void) | null;
  onArmySelect?: ((army: MatchLiveMapArmyDatum) => void) | null;
};

const cityRadius = 11;

function ownerColor(ownerLabel: string | null, visibility: "full" | "partial") {
  if (visibility === "partial") {
    return "#cbd5e1";
  }

  if (ownerLabel === null) {
    return "#f8fafc";
  }

  let hash = 0;
  for (const character of ownerLabel) {
    hash = (hash * 31 + character.charCodeAt(0)) >>> 0;
  }

  const palette = ["#2563eb", "#dc2626", "#059669", "#d97706", "#7c3aed", "#0891b2"];
  return palette[hash % palette.length];
}

function cityOwnerText(city: MatchLiveMapCityDatum, perspective: "spectator" | "player") {
  if (city.ownerVisibility === "partial") {
    return "Owner hidden";
  }

  if (city.ownerLabel === null) {
    return "Neutral";
  }

  return perspective === "player" ? `Owner ${city.ownerLabel}` : city.ownerLabel;
}

function cityGarrisonText(city: MatchLiveMapCityDatum) {
  return city.garrisonLabel === null ? "Garrison hidden" : `Garrison ${city.garrisonLabel}`;
}

function armySummaryText(army: MatchLiveMapArmyDatum) {
  if (army.visibility === "partial") {
    return `${army.ownerLabel} army hidden near ${army.cityName}`;
  }

  return `${army.ownerLabel} army ${army.troopsLabel ?? "hidden"} at ${army.cityName}`;
}

function citySelectionLabel(city: MatchLiveMapCityDatum) {
  return `Select city ${city.cityName}`;
}

function armySelectionLabel(army: MatchLiveMapArmyDatum) {
  return army.visibility === "partial"
    ? `Select army ${army.armyId} near ${army.cityName}`
    : `Select army ${army.armyId} at ${army.cityName}`;
}

function formatTicksRemaining(ticksRemaining: number) {
  return `ETA ${ticksRemaining} ${ticksRemaining === 1 ? "tick" : "ticks"}`;
}

function formatTransitPath(pathCityIds: string[], cityNamesById: Map<string, string>) {
  return pathCityIds
    .map((cityId) => cityNamesById.get(cityId) ?? cityId)
    .join(" to ");
}

function canRenderTransitGeometry(army: MatchLiveMapArmyDatum) {
  return (
    army.visibility === "full" &&
    army.transit.status === "in_transit" &&
    army.transit.destinationCityId !== null &&
    army.transit.pathCityIds !== null &&
    army.transit.pathCityIds.length >= 2
  );
}

export function describeTransitMapText(
  army: MatchLiveMapArmyDatum,
  cityNamesById: Map<string, string>
) {
  if (army.transit.status !== "in_transit" || army.transit.ticksRemaining <= 0) {
    return null;
  }

  if (canRenderTransitGeometry(army)) {
    const destinationCityName =
      cityNamesById.get(army.transit.destinationCityId ?? "") ?? army.transit.destinationCityId;
    const pathLabel = formatTransitPath(army.transit.pathCityIds ?? [], cityNamesById);

    return `${army.ownerLabel} marching ${army.cityName} to ${destinationCityName} via ${pathLabel} • ${formatTicksRemaining(army.transit.ticksRemaining)}`;
  }

  return `${army.ownerLabel} march in progress • ${formatTicksRemaining(army.transit.ticksRemaining)}`;
}

export function describeTransitListText(
  army: MatchLiveMapArmyDatum,
  cityNamesById: Map<string, string>
) {
  if (army.transit.status !== "in_transit" || army.transit.ticksRemaining <= 0) {
    return null;
  }

  if (army.visibility === "full" && army.transit.destinationCityId !== null) {
    const destinationCityName =
      cityNamesById.get(army.transit.destinationCityId) ?? army.transit.destinationCityId;
    return `${army.ownerLabel} march ${army.cityName} to ${destinationCityName} • ${formatTicksRemaining(army.transit.ticksRemaining)}`;
  }

  return `${army.ownerLabel} march in progress • ${formatTicksRemaining(army.transit.ticksRemaining)}`;
}

function handleSvgButtonKeyDown(event: KeyboardEvent<SVGGElement>, activate: () => void) {
  if (event.key !== "Enter" && event.key !== " ") {
    return;
  }

  event.preventDefault();
  activate();
}

export function MatchLiveMap({
  mapLayout,
  liveStatus,
  tick,
  perspective,
  cities,
  armies,
  selectedCityId = null,
  selectedArmyId = null,
  onCitySelect = null,
  onArmySelect = null
}: MatchLiveMapProps) {
  const cityOverlays = new Map(cities.map((city) => [city.cityId, city]));
  const armyOverlaysByCity = new Map<string, MatchLiveMapArmyDatum[]>();
  const canonicalCities = mapLayout.cities;
  const canonicalEdges = mapLayout.edges;
  const citiesById = new Map(canonicalCities.map((city) => [city.id, city]));
  const cityNamesById = new Map(canonicalCities.map((city) => [city.id, city.name]));

  for (const army of armies) {
    const currentArmies = armyOverlaysByCity.get(army.cityId) ?? [];
    currentArmies.push(army);
    armyOverlaysByCity.set(army.cityId, currentArmies);
  }

  const visibleTransitArmies =
    liveStatus === "live"
      ? armies.filter((army) => army.transit.status === "in_transit" && army.transit.ticksRemaining > 0)
      : [];

  const statusMessage =
    liveStatus === "not_live"
      ? perspective === "spectator"
        ? "Spectator feed offline"
        : "Player feed offline"
      : null;

  return (
    <section className="panel panel-section" aria-label="Britain strategic map">
      <div className="section-heading">
        <h2>Britain strategic map</h2>
        <span className="status-pill">{liveStatus === "live" ? "Live" : "Not live"}</span>
      </div>

      <p>
        {tick === null
          ? "No live strategic map data is available yet."
          : `Tick ${tick}`}
      </p>
      {statusMessage ? <p>{statusMessage}</p> : null}

      <svg
        aria-label="Britain board"
        viewBox={mapLayout.viewBox}
        width="100%"
        height="100%"
        style={{
          width: "100%",
          maxWidth: "48rem",
          height: "auto",
          border: "1px solid #cbd5e1",
          borderRadius: "0.75rem",
          background: "linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%)",
          padding: "0.75rem"
        }}
      >
        <title>Britain strategic map</title>
        <rect width={mapLayout.width} height={mapLayout.height} fill="#f8fafc" rx="18" />

        {canonicalEdges.map((edge) => {
          const cityA = citiesById.get(edge.cityA) ?? null;
          const cityB = citiesById.get(edge.cityB) ?? null;

          if (cityA === null || cityB === null) {
            return null;
          }

          return (
            <line
              key={edge.id}
              x1={cityA.x + 48}
              y1={cityA.y + 48}
              x2={cityB.x + 48}
              y2={cityB.y + 48}
              stroke={edge.traversalMode === "sea" ? "#0f766e" : "#94a3b8"}
              strokeDasharray={edge.traversalMode === "sea" ? "8 6" : undefined}
              strokeWidth={edge.traversalMode === "sea" ? 4 : 3}
            />
          );
        })}

        {visibleTransitArmies.map((army) => {
          if (!canRenderTransitGeometry(army)) {
            return null;
          }

          const pathCities = (army.transit.pathCityIds ?? [])
            .map((cityId) => citiesById.get(cityId) ?? null)
            .filter((city): city is NonNullable<typeof city> => city !== null);

          if (pathCities.length < 2) {
            return null;
          }

          const destinationCityName =
            cityNamesById.get(army.transit.destinationCityId ?? "") ?? army.transit.destinationCityId;

          return (
            <polyline
              key={`transit-${army.armyId}`}
              aria-label={`Transit overlay ${army.ownerLabel} ${army.cityName} to ${destinationCityName}`}
              points={pathCities.map((city) => `${city.x + 48},${city.y + 48}`).join(" ")}
              fill="none"
              stroke={perspective === "spectator" ? "#0f766e" : "#2563eb"}
              strokeDasharray="10 6"
              strokeWidth={5}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          );
        })}

        {canonicalCities.map((city) => {
          const cityOverlay = cityOverlays.get(city.id) ?? null;
          const visibleArmies = armyOverlaysByCity.get(city.id) ?? [];
          const isSelectedCity = cityOverlay !== null && selectedCityId === cityOverlay.cityId;

          return (
            <g key={city.id}>
              {cityOverlay === null ? (
                <circle
                  cx={city.x + 48}
                  cy={city.y + 48}
                  r={cityRadius}
                  fill={ownerColor(null, "partial")}
                  stroke="#0f172a"
                  strokeWidth={2}
                />
              ) : (
                <g
                  role="button"
                  tabIndex={0}
                  aria-label={citySelectionLabel(cityOverlay)}
                  aria-pressed={isSelectedCity}
                  onClick={() => onCitySelect?.(cityOverlay)}
                  onKeyDown={(event) => handleSvgButtonKeyDown(event, () => onCitySelect?.(cityOverlay))}
                  style={{ cursor: "pointer" }}
                >
                  <circle
                    cx={city.x + 48}
                    cy={city.y + 48}
                    r={cityRadius + (isSelectedCity ? 4 : 0)}
                    fill={isSelectedCity ? "#fef3c7" : ownerColor(cityOverlay.ownerLabel, cityOverlay.ownerVisibility)}
                    stroke={isSelectedCity ? "#b45309" : "#0f172a"}
                    strokeWidth={isSelectedCity ? 4 : 2}
                  />
                </g>
              )}
              {visibleArmies.map((army, armyIndex) => {
                const isSelectedArmy = selectedArmyId === army.armyId;
                const offsetY = armyIndex * 18;

                return (
                  <g
                    key={army.armyId}
                    role="button"
                    tabIndex={0}
                    aria-label={armySelectionLabel(army)}
                    aria-pressed={isSelectedArmy}
                    onClick={() => onArmySelect?.(army)}
                    onKeyDown={(event) => handleSvgButtonKeyDown(event, () => onArmySelect?.(army))}
                    style={{ cursor: "pointer" }}
                  >
                    <circle
                      cx={city.x + 66}
                      cy={city.y + 36 - offsetY}
                      r={isSelectedArmy ? 9 : 7}
                      fill={isSelectedArmy ? "#f59e0b" : "#111827"}
                      stroke="#f8fafc"
                      strokeWidth={2}
                    />
                  </g>
                );
              })}
              <text
                x={city.x + 48}
                y={city.y + 72}
                fontSize="16"
                fontWeight="700"
                textAnchor="middle"
                fill="#0f172a"
              >
                {city.name}
              </text>
            </g>
          );
        })}
      </svg>

      <ul className="roster-list" aria-label="Strategic city states">
        {cities.length === 0 ? (
          <li className="roster-row">
            <span>No visible city overlays yet.</span>
          </li>
        ) : (
          cities.map((city) => (
            <li
              key={city.cityId}
              className="roster-row"
              style={selectedCityId === city.cityId ? { borderColor: "#b45309", borderWidth: "2px" } : undefined}
            >
              <span>{cityOwnerText(city, perspective)}</span>
              <span>{cityGarrisonText(city)}</span>
            </li>
          ))
        )}
      </ul>

      <ul className="roster-list" aria-label="Strategic army states">
        {armies.length === 0 ? (
          <li className="roster-row">
            <span>No visible army overlays yet.</span>
          </li>
        ) : (
          armies.map((army) => (
            <li
              key={army.armyId}
              className="roster-row"
              style={selectedArmyId === army.armyId ? { borderColor: "#b45309", borderWidth: "2px" } : undefined}
            >
              <span>{armySummaryText(army)}</span>
            </li>
          ))
        )}
      </ul>

      <ul className="roster-list" aria-label="Transit overlays">
        {visibleTransitArmies.length === 0 ? (
          <li className="roster-row">
            <span>
              {liveStatus === "not_live"
                ? "No visible transit overlays in the last confirmed update."
                : "No visible transit overlays in this update."}
            </span>
          </li>
        ) : (
          visibleTransitArmies.map((army) => {
            const summaryText = describeTransitMapText(army, cityNamesById);

            if (summaryText === null) {
              return null;
            }

            return (
              <li key={`transit-summary-${army.armyId}`} className="roster-row">
                <span>{summaryText}</span>
              </li>
            );
          })
        )}
      </ul>
    </section>
  );
}
