import type {
  AllianceRecord,
  GroupChatRecord,
  GroupMessageRecord,
  PlayerMatchEnvelope,
  TreatyRecord,
  VisibleArmyState
} from "../../../lib/types";
import { describeTransitListText, type MatchLiveMapArmyDatum } from "../match-live-map";

type HumanMatchLiveSummaryPanelsProps = {
  envelope: PlayerMatchEnvelope;
  liveStatus: "live" | "not_live";
  mapArmies: MatchLiveMapArmyDatum[];
  cityNamesById: Map<string, string>;
  latestWorldMessage: PlayerMatchEnvelope["data"]["world_messages"][number] | null;
  latestDirectMessage: PlayerMatchEnvelope["data"]["direct_messages"][number] | null;
  latestGroupChat: GroupChatRecord | null;
  latestGroupMessage: GroupMessageRecord | null;
  latestTreaty: TreatyRecord | null;
  latestAlliance: AllianceRecord | null;
  partialArmy: VisibleArmyState | null;
};

const resourceRows: Array<{
  label: string;
  value: (envelope: PlayerMatchEnvelope) => number | string;
}> = [
  { label: "Food", value: (envelope) => envelope.data.state.resources.food },
  { label: "Production", value: (envelope) => envelope.data.state.resources.production },
  { label: "Money", value: (envelope) => envelope.data.state.resources.money }
];

function SummaryRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metadata-row">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function describeArmy(army: VisibleArmyState): string {
  const location = army.location ?? army.destination ?? "in transit";
  const troops = typeof army.troops === "number" ? `${army.troops} troops` : "unknown strength";
  return `${army.owner} at ${location} with ${troops} (${army.visibility})`;
}

function describeGroupChat(groupChat: GroupChatRecord | null, groupMessage: GroupMessageRecord | null): string {
  if (!groupChat) {
    return "No alliance or group chat summary yet.";
  }

  if (!groupMessage || groupMessage.group_chat_id !== groupChat.group_chat_id) {
    return groupChat.name;
  }

  return `${groupChat.name}: ${groupMessage.content}`;
}

function describeTreaty(treaty: TreatyRecord | null): string {
  if (!treaty) {
    return "No treaty summary yet.";
  }

  return `${treaty.treaty_type} ${treaty.status} between ${treaty.player_a_id} and ${treaty.player_b_id}`;
}

function describeAlliance(alliance: AllianceRecord | null): string {
  if (!alliance) {
    return "No alliance summary yet.";
  }

  return `Alliance ${alliance.name} led by ${alliance.leader_id}`;
}

export function HumanMatchLiveSummaryPanels({
  envelope,
  liveStatus,
  mapArmies,
  cityNamesById,
  latestWorldMessage,
  latestDirectMessage,
  latestGroupChat,
  latestGroupMessage,
  latestTreaty,
  latestAlliance,
  partialArmy
}: HumanMatchLiveSummaryPanelsProps) {
  return (
    <>
      <section className="panel panel-section">
        <div className="section-heading">
          <h2>Live player state</h2>
          <span className="status-pill">{liveStatus === "live" ? "Live" : "Not live"}</span>
        </div>
        <p>Fog-filtered state plus player-safe diplomacy and chat summaries from the current websocket snapshot.</p>
      </section>

      <dl className="panel panel-grid" aria-label="Live player summary">
        <SummaryRow label="Match ID" value={envelope.data.match_id} />
        <SummaryRow label="Viewing player" value={envelope.data.player_id} />
        <SummaryRow label="Tick" value={envelope.data.state.tick} />
        <SummaryRow label="Visible cities" value={Object.keys(envelope.data.state.cities).length} />
        <SummaryRow label="Visible armies" value={envelope.data.state.visible_armies.length} />
        <SummaryRow label="Alliance" value={envelope.data.state.alliance_id ?? "No alliance"} />
      </dl>

      <section className="panel panel-section">
        <h2>Resources</h2>
        <ul className="roster-list" aria-label="Player resources">
          {resourceRows.map((row) => (
            <li key={row.label} className="roster-row">
              <span>{`${row.label} ${row.value(envelope)}`}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="panel panel-section">
        <h2>Fog-filtered movement</h2>
        {envelope.data.state.visible_armies.length === 0 ? (
          <p>No player-safe army movement is visible in this update.</p>
        ) : (
          <ul className="roster-list" aria-label="Visible player armies">
            {envelope.data.state.visible_armies.map((army) => {
              const mapArmy = mapArmies.find((entry) => entry.armyId === army.id) ?? null;
              const transitText = mapArmy === null ? null : describeTransitListText(mapArmy, cityNamesById);

              return (
                <li key={army.id} className="roster-row">
                  <span>{transitText ?? describeArmy(army)}</span>
                </li>
              );
            })}
          </ul>
        )}
        {partialArmy ? <p>{`Visible enemy army near ${partialArmy.destination ?? partialArmy.location ?? "the frontier"}`}</p> : null}
      </section>

      <section className="panel panel-section">
        <h2>Chat and diplomacy</h2>
        <ul className="roster-list" aria-label="Player chat and diplomacy summaries">
          <li className="roster-row">
            <span>{latestWorldMessage ? latestWorldMessage.content : "No world message yet."}</span>
          </li>
          <li className="roster-row">
            <span>{latestDirectMessage ? latestDirectMessage.content : "No direct message yet."}</span>
          </li>
          <li className="roster-row">
            <span>{describeGroupChat(latestGroupChat, latestGroupMessage)}</span>
          </li>
          <li className="roster-row">
            <span>{describeTreaty(latestTreaty)}</span>
          </li>
          <li className="roster-row">
            <span>{describeAlliance(latestAlliance)}</span>
          </li>
        </ul>
      </section>
    </>
  );
}
