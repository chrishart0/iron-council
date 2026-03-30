import type { SpectatorMatchEnvelope } from "../../lib/types";

type MatchLiveViewProps = {
  envelope: SpectatorMatchEnvelope;
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

export function MatchLiveView({ envelope, liveStatus }: MatchLiveViewProps) {
  const latestWorldMessage = envelope.data.world_messages.at(-1) ?? null;

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
        <h2>Latest world message</h2>
        {latestWorldMessage === null ? (
          <p>No public world message has been broadcast yet.</p>
        ) : (
          <p>{latestWorldMessage.content}</p>
        )}
      </section>
    </>
  );
}
