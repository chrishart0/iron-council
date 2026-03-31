import type {
  PublicMatchRosterRow,
  SpectatorMatchEnvelope,
  TreatyRecord,
  AllianceRecord
} from "../../lib/types";
import type { BritainMapLayout } from "../../lib/britain-map";
import { MatchLiveMap, type MatchLiveMapArmyDatum, type MatchLiveMapCityDatum } from "./match-live-map";

type MatchLiveViewProps = {
  envelope: SpectatorMatchEnvelope;
  mapLayout: BritainMapLayout;
  roster: PublicMatchRosterRow[];
  liveStatus: "live" | "not_live";
};

const summaryRows: Array<{
  label: string;
  value: (envelope: SpectatorMatchEnvelope) => string | number;
}> = [
  { label: "Match ID", value: (envelope) => envelope.data.match_id },
  { label: "Tick", value: (envelope) => envelope.data.state.tick },
  { label: "Cities", value: (envelope) => Object.keys(envelope.data.state.cities).length },
  { label: "Armies", value: (envelope) => envelope.data.state.armies.length },
  { label: "Players", value: (envelope) => Object.keys(envelope.data.state.players).length },
  {
    label: "World messages",
    value: (envelope) => envelope.data.world_messages.length
  },
  { label: "Treaties", value: (envelope) => envelope.data.treaties.length },
  { label: "Alliances", value: (envelope) => envelope.data.alliances.length }
];

type TerritoryPressureEntry = {
  key: string;
  label: string;
  citiesHeld: number;
};

function formatCitiesHeld(count: number) {
  return `${count} ${count === 1 ? "city" : "cities"}`;
}

export function MatchLiveView({ envelope, mapLayout, roster, liveStatus }: MatchLiveViewProps) {
  const playerLabels = new Map(roster.map((entry) => [entry.player_id, entry.display_name]));
  const allianceLabels = new Map(
    envelope.data.alliances.map((alliance) => [alliance.alliance_id, alliance.name])
  );
  const resolvePlayerLabel = (playerId: string) => playerLabels.get(playerId) ?? playerId;
  const resolveAllianceLabel = (allianceId: string) => allianceLabels.get(allianceId) ?? allianceId;
  const territoryPressure = new Map<string, TerritoryPressureEntry>();

  for (const city of Object.values(envelope.data.state.cities)) {
    if (city.owner === null) {
      continue;
    }

    const playerState = envelope.data.state.players[city.owner];
    const allianceId = typeof playerState?.alliance_id === "string" ? playerState.alliance_id : null;
    const key = allianceId === null ? `player:${city.owner}` : `alliance:${allianceId}`;
    const label = allianceId === null ? resolvePlayerLabel(city.owner) : resolveAllianceLabel(allianceId);
    const currentEntry = territoryPressure.get(key);

    territoryPressure.set(key, {
      key,
      label,
      citiesHeld: (currentEntry?.citiesHeld ?? 0) + 1
    });
  }

  const territoryPressureRows = Array.from(territoryPressure.values()).sort((left, right) => {
    if (right.citiesHeld !== left.citiesHeld) {
      return right.citiesHeld - left.citiesHeld;
    }

    return left.label.localeCompare(right.label);
  });
  const visibleCityCount = territoryPressureRows.reduce((total, entry) => total + entry.citiesHeld, 0);
  const victoryLabel =
    envelope.data.state.victory.leading_alliance === null
      ? null
      : resolveAllianceLabel(envelope.data.state.victory.leading_alliance);
  const mapCities: MatchLiveMapCityDatum[] = Object.entries(envelope.data.state.cities)
    .map(([cityId, city]) => ({
      cityId,
      cityName: cityId.charAt(0).toUpperCase() + cityId.slice(1),
      ownerLabel: city.owner === null ? null : resolvePlayerLabel(city.owner),
      ownerVisibility: "full" as const,
      garrisonLabel: String(city.garrison)
    }))
    .sort((left, right) => left.cityName.localeCompare(right.cityName));
  const mapArmies = envelope.data.state.armies
    .flatMap<MatchLiveMapArmyDatum>((army) => {
      const cityId = army.location ?? army.destination;

      if (cityId === null) {
        return [];
      }

      return [{
        armyId: army.id,
        cityId,
        cityName: cityId.charAt(0).toUpperCase() + cityId.slice(1),
        ownerLabel: resolvePlayerLabel(army.owner),
        troopsLabel: String(army.troops),
        visibility: "full" as const
      }];
    })
    .sort((left, right) => left.cityName.localeCompare(right.cityName));

  const renderUnavailable = (message: string) => {
    if (liveStatus === "not_live") {
      return <p>{message}</p>;
    }

    return null;
  };

  const renderTreatySummary = (treaty: TreatyRecord) => {
    const treatyType = treaty.treaty_type.replaceAll("_", " ");
    return `${resolvePlayerLabel(treaty.player_a_id)} and ${resolvePlayerLabel(
      treaty.player_b_id
    )} • ${treatyType} • ${treaty.status}`;
  };

  const renderAllianceSummary = (alliance: AllianceRecord) => {
    const memberLabels = alliance.members.map((member) => resolvePlayerLabel(member.player_id));
    return `${alliance.name}: ${memberLabels.join(", ")}`;
  };

  return (
    <>
      <section className="panel panel-section">
        <div className="section-heading">
          <h2>Live spectator state</h2>
          <span className="status-pill">{liveStatus === "live" ? "Live" : "Not live"}</span>
        </div>
        <p>Read-only spectator-safe state from the shipped match websocket contract.</p>
      </section>

      <MatchLiveMap
        mapLayout={mapLayout}
        liveStatus={liveStatus}
        tick={envelope.data.state.tick}
        perspective="spectator"
        cities={mapCities}
        armies={mapArmies}
      />

      <dl className="panel panel-grid" aria-label="Live spectator summary">
        {summaryRows.map((row) => (
          <div key={row.label} className="metadata-row">
            <dt>{row.label}</dt>
            <dd>{row.value(envelope)}</dd>
          </div>
        ))}
      </dl>

      <section className="panel panel-section">
        <h2>Current movement</h2>
        {envelope.data.state.armies.length === 0 ? (
          <p>No public army movement is visible in this update.</p>
        ) : (
          <ul className="roster-list" aria-label="Visible armies">
            {envelope.data.state.armies.map((army) => (
              <li key={army.id} className="roster-row">
                <span>{army.owner}</span>
                <span>{army.location ?? army.destination ?? "In transit"}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="panel panel-section">
        <h2>Territory pressure</h2>
        {territoryPressureRows.length === 0 ? (
          <p>No owned cities are visible in the current spectator update yet.</p>
        ) : (
          <ul className="roster-list" aria-label="Territory pressure">
            {territoryPressureRows.map((entry) => (
              <li key={entry.key} className="roster-row">
                <span>{entry.label}</span>
                <span>{`${formatCitiesHeld(entry.citiesHeld)} held`}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="panel panel-section">
        <h2>Victory context</h2>
        {visibleCityCount === 0 ? (
          <>
            <p>No owned cities are visible in the current spectator update yet.</p>
            <p>No coalition is currently on a victory countdown.</p>
          </>
        ) : (
          <>
            {territoryPressureRows.map((entry) => (
              <p key={entry.key}>{`${entry.label} holds ${entry.citiesHeld} visible ${
                entry.citiesHeld === 1 ? "city" : "cities"
              }.`}</p>
            ))}
            {victoryLabel === null || envelope.data.state.victory.countdown_ticks_remaining === null ? (
              <p>No coalition is currently on a victory countdown.</p>
            ) : (
              <>
                <p>{`${victoryLabel} leads the victory race with ${envelope.data.state.victory.cities_held} of ${envelope.data.state.victory.threshold} cities.`}</p>
                <p>{`Victory countdown: ${envelope.data.state.victory.countdown_ticks_remaining} ticks remaining.`}</p>
              </>
            )}
          </>
        )}
      </section>

      <section className="panel panel-section">
        <h2>World chat</h2>
        {renderUnavailable("World chat is unavailable while the spectator feed is not live.") ??
        (envelope.data.world_messages.length === 0 ? (
          <p>No public world chat has been broadcast yet.</p>
        ) : (
          <ul className="roster-list" aria-label="World chat">
            {envelope.data.world_messages
              .slice(-5)
              .toReversed()
              .map((message) => (
                <li key={message.message_id} className="roster-row">
                  <span>{`${resolvePlayerLabel(message.sender_id)}: ${message.content}`}</span>
                </li>
              ))}
          </ul>
        ))}
      </section>

      <section className="panel panel-section">
        <h2>Treaty status</h2>
        {renderUnavailable("Treaty status is unavailable while the spectator feed is not live.") ??
        (envelope.data.treaties.length === 0 ? (
          <p>No public treaties are active right now.</p>
        ) : (
          <ul className="roster-list" aria-label="Treaty status">
            {envelope.data.treaties.map((treaty) => (
              <li key={treaty.treaty_id} className="roster-row">
                <span>{renderTreatySummary(treaty)}</span>
              </li>
            ))}
          </ul>
        ))}
      </section>

      <section className="panel panel-section">
        <h2>Alliance membership</h2>
        {renderUnavailable(
          "Alliance membership is unavailable while the spectator feed is not live."
        ) ??
        (envelope.data.alliances.length === 0 ? (
          <p>No public alliances are visible right now.</p>
        ) : (
          <ul className="roster-list" aria-label="Alliance membership">
            {envelope.data.alliances.map((alliance) => (
              <li key={alliance.alliance_id} className="roster-row">
                <span>{renderAllianceSummary(alliance)}</span>
              </li>
            ))}
          </ul>
        ))}
      </section>
    </>
  );
}
