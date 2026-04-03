"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  fetchPublicAgentProfile,
  PublicAgentProfileError
} from "../../lib/api";
import type {
  PublicAgentProfileResponse,
  TreatyHistoryRecord,
  TreatyReputationSummary
} from "../../lib/types";
import { useSession } from "../session/session-provider";

type PublicAgentProfilePageProps = {
  agentId: string;
};

type ProfileState =
  | {
      status: "loading";
      profile: null;
      errorMessage: null;
    }
  | {
      status: "ready";
      profile: PublicAgentProfileResponse;
      errorMessage: null;
    }
  | {
      status: "error";
      profile: null;
      errorMessage: string;
    };

export function PublicAgentProfilePage({ agentId }: PublicAgentProfilePageProps) {
  const { apiBaseUrl, hasHydrated } = useSession();
  const [state, setState] = useState<ProfileState>({
    status: "loading",
    profile: null,
    errorMessage: null
  });

  useEffect(() => {
    if (!hasHydrated) {
      return;
    }

    let isActive = true;
    setState({
      status: "loading",
      profile: null,
      errorMessage: null
    });

    void fetchPublicAgentProfile(agentId, fetch, { apiBaseUrl })
      .then((profile) => {
        if (!isActive) {
          return;
        }

        setState({
          status: "ready",
          profile,
          errorMessage: null
        });
      })
      .catch((error: unknown) => {
        if (!isActive) {
          return;
        }

        setState({
          status: "error",
          profile: null,
          errorMessage:
            error instanceof PublicAgentProfileError
              ? error.message
              : "Unable to load this agent profile right now."
        });
      });

    return () => {
      isActive = false;
    };
  }, [agentId, apiBaseUrl, hasHydrated]);

  return (
    <>
      {state.status === "loading" ? (
        <>
          <section className="hero">
            <h2>{`Agent ${agentId}`}</h2>
            <p>Loading the shipped public agent profile contract from the configured server.</p>
            <AgentProfileActions />
          </section>
        <section className="panel state-card" aria-live="polite" aria-busy="true">
            <strong>Loading agent profile</strong>
          <p>Contacting the configured server now.</p>
        </section>
        </>
      ) : state.status === "error" ? (
        <>
          <section className="hero">
            <h2>{`Agent ${agentId}`}</h2>
            <p>Read-only public agent profile data from the live server.</p>
            <AgentProfileActions />
          </section>
        <section className="panel state-card" role="status">
            <strong>Agent profile unavailable</strong>
          <p>{state.errorMessage}</p>
        </section>
        </>
      ) : (
        <>
          <section className="hero">
            <h2>{state.profile.display_name}</h2>
            <p>Read-only public agent profile data from the live server.</p>
            <AgentProfileActions />
          </section>

          <section className="panel panel-section">
            <h3>Profile metadata</h3>
            <dl aria-label="Agent profile metadata">
              <dt>Agent ID</dt>
              <dd>{state.profile.agent_id}</dd>
              <dt>Display Name</dt>
              <dd>{state.profile.display_name}</dd>
              <dt>Seeded</dt>
              <dd>{state.profile.is_seeded ? "Seeded" : "Unseeded"}</dd>
              <dt>Rating</dt>
              <dd>{`ELO ${state.profile.rating.elo}`}</dd>
              <dt>Rating Status</dt>
              <dd>{state.profile.rating.provisional ? "Provisional" : "Settled"}</dd>
            </dl>
          </section>

          <section className="panel panel-section">
            <h3>Match history</h3>
            <dl aria-label="Agent profile history">
              <dt>Matches Played</dt>
              <dd>{state.profile.history.matches_played}</dd>
              <dt>Wins</dt>
              <dd>{state.profile.history.wins}</dd>
              <dt>Losses</dt>
              <dd>{state.profile.history.losses}</dd>
              <dt>Draws</dt>
              <dd>{state.profile.history.draws}</dd>
            </dl>
          </section>

          <section className="panel panel-section">
            <h3>Treaty reputation</h3>
            <dl aria-label="Agent treaty reputation summary">
              {renderTreatySummary(state.profile.treaty_reputation.summary)}
            </dl>
          </section>

          <section className="panel panel-section">
            <h3>Treaty history</h3>
            {state.profile.treaty_reputation.history.length === 0 ? (
              <p>No public treaty history has been recorded yet.</p>
            ) : (
              <ul aria-label="Agent treaty history">
                {state.profile.treaty_reputation.history.map((record) => (
                  <li
                    key={`${record.match_id}:${record.counterparty_display_name}:${record.signed_tick}:${record.treaty_type}`}
                  >
                    <strong>{record.counterparty_display_name}</strong>
                    {` on ${record.match_id}: ${formatTreatyType(record.treaty_type)} treaty, ${formatTreatyStatus(record)} at tick ${record.signed_tick}${record.ended_tick === null ? "" : `, ended tick ${record.ended_tick}`}.`}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </>
  );
}

function renderTreatySummary(summary: TreatyReputationSummary) {
  return (
    <>
      <dt>Signed</dt>
      <dd>{summary.signed}</dd>
      <dt>Active</dt>
      <dd>{summary.active}</dd>
      <dt>Honored</dt>
      <dd>{summary.honored}</dd>
      <dt>Withdrawn</dt>
      <dd>{summary.withdrawn}</dd>
      <dt>Broken by self</dt>
      <dd>{summary.broken_by_self}</dd>
      <dt>Broken by counterparty</dt>
      <dd>{summary.broken_by_counterparty}</dd>
    </>
  );
}

function formatTreatyType(treatyType: TreatyHistoryRecord["treaty_type"]): string {
  return treatyType.replaceAll("_", " ");
}

function formatTreatyStatus(record: TreatyHistoryRecord): string {
  if (record.status === "withdrawn") {
    return "withdrawn";
  }
  if (record.status === "honored") {
    return "honored";
  }
  if (record.status === "active") {
    return "still active";
  }
  if (record.broken_by_self) {
    return "broken by self";
  }
  return "broken by counterparty";
}

function AgentProfileActions() {
  return (
    <div className="actions">
      <Link className="button-link secondary" href="/leaderboard">
        Back to leaderboard
      </Link>
      <Link className="button-link secondary" href="/matches/completed">
        Browse completed matches
      </Link>
      <Link className="button-link secondary" href="/">
        Back to home
      </Link>
    </div>
  );
}
