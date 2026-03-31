import Link from "next/link";
import type { PublicMatchDetailResponse } from "../../lib/types";

type MatchDetailProps = {
  match: PublicMatchDetailResponse;
};

const metadataRows: Array<{
  label: string;
  value: (match: PublicMatchDetailResponse) => string | number;
}> = [
  { label: "Match ID", value: (match) => match.match_id },
  { label: "Status", value: (match) => match.status },
  { label: "Map", value: (match) => match.map },
  { label: "Tick", value: (match) => match.tick },
  { label: "Tick interval", value: (match) => `${match.tick_interval_seconds}s` },
  {
    label: "Players",
    value: (match) => `${match.current_player_count} / ${match.max_player_count}`
  },
  { label: "Open slots", value: (match) => match.open_slot_count }
];

export function MatchDetail({ match }: MatchDetailProps) {
  return (
    <>
      <section className="hero">
        <h2>{`Public Match ${match.match_id}`}</h2>
        <p>Read-only public match metadata from the live server.</p>
        <p>Browse the public summary here, open the spectator page, or use the authenticated player page with a stored browser token.</p>
        <div className="actions">
          <Link className="button-link" href={`/matches/${match.match_id}/live`}>
            Watch live spectator view
          </Link>
          <Link className="button-link secondary" href={`/matches/${match.match_id}/play`}>
            Open authenticated player view
          </Link>
          <Link className="button-link secondary" href="/matches">
            Back to matches
          </Link>
        </div>
      </section>

      <dl className="panel panel-grid" aria-label="Match metadata">
        {metadataRows.map((row) => (
          <div key={row.label} className="metadata-row">
            <dt>{row.label}</dt>
            <dd>{row.value(match)}</dd>
          </div>
        ))}
      </dl>

      <section className="panel panel-section">
        <h2>Visible roster</h2>
        {match.roster.length === 0 ? (
          <p>No public roster entries are available yet.</p>
        ) : (
          <ul className="roster-list" aria-label="Public roster">
            {match.roster.map((entry, index) => (
              <li key={entry.player_id} className="roster-row">
                <span>{entry.display_name}</span>
                <span className="status-pill">
                  {entry.competitor_kind === "human" ? "Human" : "Agent"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
