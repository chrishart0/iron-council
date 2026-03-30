"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchPublicMatchDetail, PublicMatchDetailError } from "../../lib/api";
import type { PublicMatchDetailResponse } from "../../lib/types";
import { useSession } from "../session/session-provider";
import { MatchDetail } from "./match-detail";

type PublicMatchDetailPageProps = {
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

export function PublicMatchDetailPage({ matchId }: PublicMatchDetailPageProps) {
  const { apiBaseUrl, hasHydrated } = useSession();
  const [state, setState] = useState<MatchDetailState>({
    status: "loading",
    match: null,
    errorMessage: null
  });

  useEffect(() => {
    if (!hasHydrated) {
      return;
    }

    let isActive = true;

    setState({
      status: "loading",
      match: null,
      errorMessage: null
    });

    void fetchPublicMatchDetail(matchId, fetch, { apiBaseUrl })
      .then((match) => {
        if (!isActive) {
          return;
        }

        setState({
          status: "ready",
          match,
          errorMessage: null
        });
      })
      .catch((error: unknown) => {
        if (!isActive) {
          return;
        }

        setState({
          status: "error",
          match: null,
          errorMessage:
            error instanceof PublicMatchDetailError
              ? error.message
              : "Unable to load this public match right now."
        });
      });

    return () => {
      isActive = false;
    };
  }, [apiBaseUrl, hasHydrated, matchId]);

  if (state.status === "loading") {
    return (
      <>
        <section className="hero">
          <h2>{`Public Match ${matchId}`}</h2>
          <p>Loading compact public match metadata from the configured server.</p>
        </section>
        <section className="panel state-card" aria-live="polite" aria-busy="true">
          <strong>Loading match detail</strong>
          <p>Contacting the configured server now.</p>
        </section>
      </>
    );
  }

  if (state.status === "error") {
    return (
      <>
        <section className="hero">
          <h2>{`Public Match ${matchId}`}</h2>
          <p>Read-only public match metadata from the live server.</p>
          <div className="actions">
            <Link className="button-link secondary" href="/matches">
              Back to matches
            </Link>
          </div>
        </section>
        <section className="panel state-card" role="status">
          <strong>Match unavailable</strong>
          <p>{state.errorMessage}</p>
        </section>
      </>
    );
  }

  return <MatchDetail match={state.match} />;
}
