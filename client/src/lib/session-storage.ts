export const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
export const SESSION_STORAGE_KEY = "iron-council.client-session.v1";

export type StoredSession = {
  apiBaseUrl: string;
  bearerToken: string | null;
};

export function normalizeApiBaseUrl(value: string | null | undefined): string {
  const trimmed = value?.trim();

  if (!trimmed) {
    return DEFAULT_API_BASE_URL;
  }

  return trimmed.replace(/\/$/, "");
}

export function createDefaultSession(): StoredSession {
  return {
    apiBaseUrl: DEFAULT_API_BASE_URL,
    bearerToken: null
  };
}

export function loadStoredSession(): StoredSession {
  if (typeof window === "undefined") {
    return createDefaultSession();
  }

  const rawValue = window.localStorage.getItem(SESSION_STORAGE_KEY);

  if (!rawValue) {
    return createDefaultSession();
  }

  try {
    const payload: unknown = JSON.parse(rawValue);

    if (!isStoredSession(payload)) {
      return createDefaultSession();
    }

    return {
      apiBaseUrl: normalizeApiBaseUrl(payload.apiBaseUrl),
      bearerToken: normalizeBearerToken(payload.bearerToken)
    };
  } catch {
    return createDefaultSession();
  }
}

export function persistSession(session: StoredSession): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(
    SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: normalizeApiBaseUrl(session.apiBaseUrl),
        bearerToken: normalizeBearerToken(session.bearerToken)
      })
  );
}

export function normalizeBearerToken(value: string | null | undefined): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

function isStoredSession(payload: unknown): payload is StoredSession {
  if (typeof payload !== "object" || payload === null) {
    return false;
  }

  const candidate = payload as Record<string, unknown>;

  return (
    typeof candidate.apiBaseUrl === "string" &&
    (typeof candidate.bearerToken === "string" || candidate.bearerToken === null)
  );
}
