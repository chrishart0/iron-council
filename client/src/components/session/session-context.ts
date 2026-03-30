import { createContext } from "react";
import type { StoredSession } from "../../lib/session-storage";

export type SessionContextValue = StoredSession & {
  authStatusLabel: string;
  hasHydrated: boolean;
  isAuthenticated: boolean;
  setSession: (session: Partial<StoredSession>) => void;
};

export const SessionContext = createContext<SessionContextValue | null>(null);
