import type {
  PublicMatchRosterRow,
  SpectatorMatchEnvelope,
  TreatyRecord,
  AllianceRecord
} from "../../lib/types";

type MatchLiveViewProps = {
  envelope: SpectatorMatchEnvelope;
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

export function MatchLiveView({ envelope, roster, liveStatus }: MatchLiveViewProps) {
  const playerLabels = new Map(roster.map((entry) => [entry.player_id, entry.display_name]));
  const resolvePlayerLabel = (playerId: string) => playerLabels.get(playerId) ?? playerId;

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
