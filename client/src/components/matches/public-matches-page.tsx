"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { MatchBrowser } from "./match-browser";
import { PublicMatchesError, fetchPublicMatches } from "../../lib/api";
import type { MatchSummary } from "../../lib/types";
import { useSession } from "../session/session-provider";

type MatchesState =
  | {
      status: "loading";
      matches: MatchSummary[];
      errorMessage: null;
    }
  | {
      status: "ready";
      matches: MatchSummary[];
      errorMessage: null;
    }
  | {
      status: "error";
      matches: MatchSummary[];
      errorMessage: string;
    };

export function PublicMatchesPage() {
  const { apiBaseUrl, hasHydrated } = useSession();
  const [state, setState] = useState<MatchesState>({
    status: "loading",
    matches: [],
    errorMessage: null
  });

  useEffect(() => {
    if (!hasHydrated) {
      return;
    }

    let isActive = true;

    setState({
      status: "loading",
      matches: [],
      errorMessage: null
    });

    void fetchPublicMatches(fetch, { apiBaseUrl })
      .then(({ matches }) => {
        if (!isActive) {
          return;
        }

        setState({
          status: "ready",
          matches,
          errorMessage: null
        });
      })
      .catch((error: unknown) => {
        if (!isActive) {
          return;
        }

        setState({
          status: "error",
          matches: [],
          errorMessage:
            error instanceof PublicMatchesError
              ? error.message
              : "Unable to load public matches right now."
        });
      });

    return () => {
      isActive = false;
    };
  }, [apiBaseUrl, hasHydrated]);

  return (
    <>
      <section className="hero">
        <h2>Public Matches</h2>
        <p>
          Read-only browse data from the live server. Match actions stay out of
          scope until later authenticated stories.
        </p>
        <div className="actions">
          <Link className="button-link secondary" href="/">
            Back to home
          </Link>
        </div>
      </section>
      {state.status === "loading" ? (
        <section className="panel state-card" aria-live="polite" aria-busy="true">
          <strong>Loading public matches</strong>
          <p>Contacting the configured server now.</p>
        </section>
      ) : (
        <MatchBrowser matches={state.matches} errorMessage={state.errorMessage ?? undefined} />
      )}
    </>
  );
}
