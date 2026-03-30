import type { MatchSummary } from "../../lib/types";

type MatchBrowserProps = {
  matches?: MatchSummary[];
  errorMessage?: string;
};

const columns: Array<{ key: keyof MatchSummary | "tickInterval"; label: string }> = [
  { key: "match_id", label: "Match ID" },
  { key: "status", label: "Status" },
  { key: "map", label: "Map" },
  { key: "tick", label: "Tick" },
  { key: "tickInterval", label: "Tick interval" },
  { key: "current_player_count", label: "Current players" },
  { key: "max_player_count", label: "Max players" },
  { key: "open_slot_count", label: "Open slots" }
];

export function MatchBrowser({ matches = [], errorMessage }: MatchBrowserProps) {
  if (errorMessage) {
    return (
      <section className="panel state-card" role="status">
        <strong>Matches unavailable</strong>
        <p>{errorMessage}</p>
      </section>
    );
  }

  if (matches.length === 0) {
    return (
      <section className="panel state-card" role="status">
        <strong>No public matches yet</strong>
        <p>Start the server or create a lobby to populate this page.</p>
      </section>
    );
  }

  return (
    <section className="panel table-wrap">
      <table className="matches-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key} scope="col">
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matches.map((match) => (
            <tr key={match.match_id}>
              <td>{match.match_id}</td>
              <td>
                <span className="status-pill">{match.status}</span>
              </td>
              <td>{match.map}</td>
              <td>{match.tick}</td>
              <td>{match.tick_interval_seconds}s</td>
              <td>{match.current_player_count}</td>
              <td>{match.max_player_count}</td>
              <td>{match.open_slot_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
