import {
  type BritainMapLayout
} from "../../lib/britain-map";

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
};

type MatchLiveMapProps = {
  mapLayout: BritainMapLayout;
  liveStatus: "live" | "not_live";
  tick: number | null;
  perspective: "spectator" | "player";
  cities: MatchLiveMapCityDatum[];
  armies: MatchLiveMapArmyDatum[];
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

export function MatchLiveMap({
  mapLayout,
  liveStatus,
  tick,
  perspective,
  cities,
  armies
}: MatchLiveMapProps) {
  const cityOverlays = new Map(cities.map((city) => [city.cityId, city]));
  const armyOverlaysByCity = new Map<string, MatchLiveMapArmyDatum[]>();
  const canonicalCities = mapLayout.cities;
  const canonicalEdges = mapLayout.edges;
  const citiesById = new Map(canonicalCities.map((city) => [city.id, city]));

  for (const army of armies) {
    const currentArmies = armyOverlaysByCity.get(army.cityId) ?? [];
    currentArmies.push(army);
    armyOverlaysByCity.set(army.cityId, currentArmies);
  }

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

        {canonicalCities.map((city) => {
          const cityOverlay = cityOverlays.get(city.id) ?? null;
          const visibleArmies = armyOverlaysByCity.get(city.id) ?? [];

          return (
            <g key={city.id}>
              <circle
                cx={city.x + 48}
                cy={city.y + 48}
                r={cityRadius}
                fill={ownerColor(cityOverlay?.ownerLabel ?? null, cityOverlay?.ownerVisibility ?? "partial")}
                stroke="#0f172a"
                strokeWidth={2}
              />
              {visibleArmies.length > 0 ? (
                <circle
                  cx={city.x + 66}
                  cy={city.y + 36}
                  r={7}
                  fill="#111827"
                  stroke="#f8fafc"
                  strokeWidth={2}
                />
              ) : null}
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
            <li key={city.cityId} className="roster-row">
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
            <li key={army.armyId} className="roster-row">
              <span>{armySummaryText(army)}</span>
            </li>
          ))
        )}
      </ul>
    </section>
  );
}
