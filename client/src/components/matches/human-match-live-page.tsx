"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  buildPlayerMatchWebSocketUrl,
  fetchPublicMatchDetail,
  getPlayerWebSocketCloseMessage,
  parsePlayerMatchEnvelope,
  parseWebSocketApiErrorEnvelope,
  PublicMatchDetailError
} from "../../lib/api";
import type {
  AllianceRecord,
  GroupChatRecord,
  GroupMessageRecord,
  PlayerMatchEnvelope,
  PublicMatchDetailResponse,
  TreatyRecord,
  VisibleArmyState
} from "../../lib/types";
import { useSession } from "../session/session-provider";

type HumanMatchLivePageProps = {
  matchId: string;
};

type MatchDetailState =
  | {
      status: "loading";
      match: null;
      errorMessage: null;
    }
  | {
      status: "ready";
      match: PublicMatchDetailResponse;
      errorMessage: null;
    }
  | {
      status: "error";
      match: null;
      errorMessage: string;
    };

type LiveConnectionState =
  | {
      status: "idle" | "connecting";
      envelope: null;
      message: string | null;
    }
  | {
      status: "live";
      envelope: PlayerMatchEnvelope;
      message: string | null;
    }
  | {
      status: "not_live";
      envelope: PlayerMatchEnvelope | null;
      message: string;
    };

const resourceRows: Array<{
  label: string;
  value: (envelope: PlayerMatchEnvelope) => number | string;
}> = [
  { label: "Food", value: (envelope) => envelope.data.state.resources.food },
  { label: "Production", value: (envelope) => envelope.data.state.resources.production },
  { label: "Money", value: (envelope) => envelope.data.state.resources.money }
];

export function HumanMatchLivePage({ matchId }: HumanMatchLivePageProps) {
  const { apiBaseUrl, bearerToken, hasHydrated } = useSession();
  const [matchState, setMatchState] = useState<MatchDetailState>({
    status: "loading",
    match: null,
    errorMessage: null
  });
  const [liveState, setLiveState] = useState<LiveConnectionState>({
    status: "idle",
    envelope: null,
    message: null
  });

  useEffect(() => {
    if (!hasHydrated) {
      return;
    }

    if (!bearerToken) {
      setMatchState({
        status: "error",
        match: null,
        errorMessage: "This live player page requires a stored human bearer token before it can connect."
      });
      setLiveState({
        status: "not_live",
        envelope: null,
        message: "This live player page requires a stored human bearer token before it can connect."
      });
      return;
    }

    let isActive = true;

    setMatchState({
      status: "loading",
      match: null,
      errorMessage: null
    });
    setLiveState({
      status: "idle",
      envelope: null,
      message: null
    });

    void fetchPublicMatchDetail(matchId, fetch, { apiBaseUrl })
      .then((match) => {
        if (!isActive) {
          return;
        }

        setMatchState({
          status: "ready",
          match,
          errorMessage: null
        });
      })
      .catch((error: unknown) => {
        if (!isActive) {
          return;
        }

        const errorMessage =
          error instanceof PublicMatchDetailError
            ? error.message
            : "Unable to load this public match right now.";

        setMatchState({
          status: "error",
          match: null,
          errorMessage
        });
        setLiveState({
          status: "not_live",
          envelope: null,
          message: errorMessage
        });
      });

    return () => {
      isActive = false;
    };
  }, [apiBaseUrl, bearerToken, hasHydrated, matchId]);

  useEffect(() => {
    if (!hasHydrated || !bearerToken || matchState.status !== "ready") {
      return;
    }

    if (matchState.match.status !== "active") {
      setLiveState({
        status: "not_live",
        envelope: null,
        message: `This match is ${matchState.match.status}, so the authenticated live page is not active.`
      });
      return;
    }

    const socket = new WebSocket(buildPlayerMatchWebSocketUrl(matchId, bearerToken, { apiBaseUrl }));
    let hasClosed = false;

    setLiveState({
      status: "connecting",
      envelope: null,
      message: null
    });

    const markUnavailable = (options?: { message?: string | null; reason?: string }) => {
      if (hasClosed) {
        return;
      }

      hasClosed = true;

      setLiveState((currentState) => ({
        status: "not_live",
        envelope: currentState.envelope,
        message:
          options?.message ??
          getPlayerWebSocketCloseMessage(options?.reason ?? "") ??
          (currentState.envelope === null
            ? "Live updates are unavailable right now."
            : "Showing the last confirmed player snapshot. Reconnect to resume live updates.")
      }));
    };

    socket.onmessage = (event) => {
      try {
        const parsedPayload: unknown = JSON.parse(event.data);
        const errorEnvelope = parseWebSocketApiErrorEnvelope(parsedPayload);

        if (errorEnvelope !== null) {
          markUnavailable({ message: errorEnvelope.error.message });
          return;
        }

        const payload = parsePlayerMatchEnvelope(parsedPayload);

        setLiveState({
          status: "live",
          envelope: payload,
          message: null
        });
      } catch {
        markUnavailable();
      }
    };

    socket.onerror = () => {
      markUnavailable();
    };

    socket.onclose = (event) => {
      markUnavailable({ reason: event.reason });
    };

    return () => {
      hasClosed = true;
      socket.close();
    };
  }, [apiBaseUrl, bearerToken, hasHydrated, matchId, matchState]);

  const statusPanel =
    matchState.status === "loading" ? (
      <section className="panel state-card" aria-live="polite" aria-busy="true">
        <strong>Loading live match access</strong>
        <p>Waiting for the public match summary before opening the player websocket.</p>
      </section>
    ) : liveState.status === "connecting" ? (
      <section className="panel state-card" aria-live="polite">
        <strong>Connecting player feed</strong>
        <p>Opening the authenticated websocket now.</p>
      </section>
    ) : liveState.status === "not_live" ? (
      <section className="panel state-card" role="status">
        <strong>{liveState.envelope === null ? "Live updates unavailable" : "Live connection lost"}</strong>
        <p>{liveState.message}</p>
      </section>
    ) : null;

  return (
    <>
      <section className="hero">
        <h2>{`Live Match ${matchId}`}</h2>
        <p>Authenticated player-safe updates over the shipped match websocket contract.</p>
        <div className="actions">
          <Link className="button-link secondary" href={`/matches/${matchId}`}>
            Back to match detail
          </Link>
        </div>
      </section>

      {statusPanel}

      {liveState.envelope !== null ? (
        <HumanMatchLiveSnapshot
          envelope={liveState.envelope}
          liveStatus={liveState.status === "live" ? "live" : "not_live"}
        />
      ) : null}
    </>
  );
}

function HumanMatchLiveSnapshot({
  envelope,
  liveStatus
}: {
  envelope: PlayerMatchEnvelope;
  liveStatus: "live" | "not_live";
}) {
  const latestWorldMessage = envelope.data.world_messages.at(-1) ?? null;
  const latestDirectMessage = envelope.data.direct_messages.at(-1) ?? null;
  const latestGroupChat = envelope.data.group_chats.at(-1) ?? null;
  const latestGroupMessage = envelope.data.group_messages.at(-1) ?? null;
  const latestTreaty = envelope.data.treaties.at(-1) ?? null;
  const latestAlliance = envelope.data.alliances.at(-1) ?? null;
  const partialArmy = envelope.data.state.visible_armies.find((army) => army.visibility === "partial") ?? null;

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
            {envelope.data.state.visible_armies.map((army) => (
              <li key={army.id} className="roster-row">
                <span>{describeArmy(army)}</span>
              </li>
            ))}
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

function describeGroupChat(
  groupChat: GroupChatRecord | null,
  groupMessage: GroupMessageRecord | null
): string {
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
