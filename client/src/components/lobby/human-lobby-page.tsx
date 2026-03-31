"use client";
import { FormEvent, useState } from "react";
import { createMatchLobby, joinMatchLobby, LobbyActionError, startMatchLobby } from "../../lib/api";
import type { MatchJoinResponse, MatchLobbyCreateResponse, MatchLobbyStartResponse } from "../../lib/types";
import { useSession } from "../session/session-provider";

type SuccessState =
  | { action: "create"; data: MatchLobbyCreateResponse }
  | { action: "join"; data: MatchJoinResponse }
  | { action: "start"; data: MatchLobbyStartResponse }
  | null;

type ErrorState = {
  message: string;
  code: string | null;
  statusCode: number | null;
};

export function HumanLobbyPage() {
  const { apiBaseUrl, bearerToken } = useSession();
  const [joinMatchId, setJoinMatchId] = useState("");
  const [success, setSuccess] = useState<SuccessState>(null);
  const [error, setError] = useState<ErrorState | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<false | "create" | "join" | "start">(false);

  async function run(action: "create" | "join" | "start", task: () => Promise<SuccessState>) {
    if (!bearerToken) return;
    setIsSubmitting(action);
    setError(null);
    try {
      const next = await task();
      setSuccess(next);
      if (action === "create" && next?.action === "create") {
        setJoinMatchId(next.data.match_id);
      }
      if (action === "join" && next?.action === "join") {
        setJoinMatchId(next.data.match_id);
      }
    } catch (error) {
      setError(
        error instanceof LobbyActionError
          ? { message: error.message, code: error.code, statusCode: error.statusCode }
          : {
              message: "Unable to complete the requested lobby action right now.",
              code: null,
              statusCode: null
            }
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  function submitCreate(event: FormEvent) {
    event.preventDefault();
    void run("create", async () => ({ action: "create", data: await createMatchLobby({ map: "britain", tick_interval_seconds: 20, max_players: 4, victory_city_threshold: 13, starting_cities_per_player: 2 }, bearerToken!, fetch, { apiBaseUrl }) }));
  }

  function submitJoin(event: FormEvent) {
    event.preventDefault();
    const matchId = joinMatchId.trim();
    if (!matchId) {
      setError({ message: "Enter a match id before joining.", code: null, statusCode: null });
      return;
    }
    void run("join", async () => ({ action: "join", data: await joinMatchLobby({ match_id: matchId }, bearerToken!, fetch, { apiBaseUrl }) }));
  }

  function submitStart() {
    const matchId = joinMatchId.trim() || (success && "data" in success ? success.data.match_id : "");
    if (!matchId) {
      setError({ message: "Create or join a lobby before starting it.", code: null, statusCode: null });
      return;
    }
    void run("start", async () => ({ action: "start", data: await startMatchLobby(matchId, bearerToken!, fetch, { apiBaseUrl }) }));
  }

  return (
    <>
      <section className="hero">
        <h2>Human Lobby</h2>
        <p>Create, join, and start a lobby through the shipped match routes using the stored browser bearer token.</p>
      </section>
      <section className="panel state-card lobby-grid">
        <form className="lobby-form" onSubmit={submitCreate}>
          <strong>Create lobby</strong>
          <p>Creates a standard Britain lobby with the current browser session.</p>
          <button className="button-link" type="submit" disabled={isSubmitting !== false}>
            {isSubmitting === "create" ? "Creating…" : "Create lobby"}
          </button>
        </form>
        <form className="lobby-form" onSubmit={submitJoin}>
          <strong>Join lobby</strong>
          <label className="field"><span>Match id</span><input value={joinMatchId} onChange={(e) => setJoinMatchId(e.target.value)} placeholder="match-id" /></label>
          <button className="button-link secondary" type="submit" disabled={isSubmitting !== false}>
            {isSubmitting === "join" ? "Joining…" : "Join lobby"}
          </button>
        </form>
        <div className="lobby-form">
          <strong>Start lobby</strong>
          <p>Starts the currently selected lobby when the creator and readiness checks pass.</p>
          <button className="button-link secondary" type="button" onClick={submitStart} disabled={isSubmitting !== false}>
            {isSubmitting === "start" ? "Starting…" : "Start lobby"}
          </button>
        </div>
      </section>
      {error ? (
        <section className="panel state-card" role="status">
          <strong>Lobby action failed</strong>
          <div className="panel-grid">
            <div className="metadata-row"><dt>Message</dt><dd>{error.message}</dd></div>
            {error.code ? <div className="metadata-row"><dt>Code</dt><dd>{error.code}</dd></div> : null}
            {error.statusCode !== null ? <div className="metadata-row"><dt>Status</dt><dd>{error.statusCode}</dd></div> : null}
          </div>
        </section>
      ) : null}
      {success ? <section className="panel state-card" role="status"><strong>Last confirmed action: {success.action}</strong>{success.action === "join" ? <p>{`Joined ${success.data.match_id} as ${success.data.player_id}.`}</p> : <div className="panel-grid"><div className="metadata-row"><dt>Match</dt><dd>{success.data.match_id}</dd></div><div className="metadata-row"><dt>Status</dt><dd>{success.data.status}</dd></div><div className="metadata-row"><dt>Players</dt><dd>{`${success.data.current_player_count} / ${success.data.max_player_count}`}</dd></div><div className="metadata-row"><dt>Open slots</dt><dd>{success.data.open_slot_count}</dd></div></div>}</section> : null}
    </>
  );
}
