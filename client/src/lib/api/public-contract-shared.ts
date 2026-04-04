import type { ApiErrorEnvelope } from "../types";
import { DEFAULT_API_BASE_URL, normalizeApiBaseUrl } from "../session-storage";

export function resolveApiBaseUrl(explicitBaseUrl?: string): string {
  if (explicitBaseUrl) {
    return normalizeApiBaseUrl(explicitBaseUrl);
  }

  return DEFAULT_API_BASE_URL;
}

export function hasApiErrorCode(payload: unknown, code: string): boolean {
  return isApiErrorEnvelope(payload) && payload.error.code === code;
}

export function isApiErrorEnvelope(payload: unknown): payload is ApiErrorEnvelope {
  return (
    isRecord(payload) &&
    isRecord(payload.error) &&
    typeof payload.error.code === "string" &&
    typeof payload.error.message === "string"
  );
}

export function isRecord(payload: unknown): payload is Record<string, unknown> {
  return typeof payload === "object" && payload !== null;
}
