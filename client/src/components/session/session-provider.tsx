"use client";

import { useContext, useEffect, useMemo, useState } from "react";
import { SessionContext } from "./session-context";
import {
  createDefaultSession,
  loadStoredSession,
  normalizeApiBaseUrl,
  normalizeBearerToken,
  persistSession,
  type StoredSession
} from "../../lib/session-storage";

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [session, setSessionState] = useState<StoredSession>(createDefaultSession);
  const [hasHydrated, setHasHydrated] = useState(false);

  useEffect(() => {
    setSessionState(loadStoredSession());
    setHasHydrated(true);
  }, []);

  useEffect(() => {
    if (!hasHydrated) {
      return;
    }

    persistSession(session);
  }, [hasHydrated, session]);

  const value = useMemo(
    () => ({
      ...session,
      authStatusLabel: session.bearerToken
        ? "Human token configured"
        : "Public-only session",
      hasHydrated,
      isAuthenticated: session.bearerToken !== null,
      setSession(update: Partial<StoredSession>) {
        setSessionState((currentSession) => ({
          apiBaseUrl:
            update.apiBaseUrl === undefined
              ? currentSession.apiBaseUrl
              : normalizeApiBaseUrl(update.apiBaseUrl),
          bearerToken:
            update.bearerToken === undefined
              ? currentSession.bearerToken
              : normalizeBearerToken(update.bearerToken)
        }));
      }
    }),
    [hasHydrated, session]
  );

  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  );
}

export function useSession() {
  const value = useContext(SessionContext);

  if (value === null) {
    throw new Error("useSession must be used within a SessionProvider");
  }

  return value;
}
