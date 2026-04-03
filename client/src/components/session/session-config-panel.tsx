"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ApiKeyLifecycleError, createOwnedApiKey, fetchOwnedApiKeys, revokeOwnedApiKey } from "../../lib/api";
import type { OwnedApiKeySummary } from "../../lib/types";
import { useSession } from "./session-provider";

const API_KEY_ERROR_FALLBACK_MESSAGE = "Unable to manage account API keys right now.";

export function SessionConfigPanel() {
  const { apiBaseUrl, bearerToken, setSession } = useSession();
  const [draftApiBaseUrl, setDraftApiBaseUrl] = useState(apiBaseUrl);
  const [draftBearerToken, setDraftBearerToken] = useState(bearerToken ?? "");
  const [savedMessage, setSavedMessage] = useState("");
  const [ownedKeys, setOwnedKeys] = useState<OwnedApiKeySummary[]>([]);
  const [keysStatus, setKeysStatus] = useState<"idle" | "loading" | "ready">("idle");
  const [keysError, setKeysError] = useState<string | null>(null);
  const [createdSecret, setCreatedSecret] = useState<string | null>(null);
  const [isCreatingKey, setIsCreatingKey] = useState(false);
  const [revokingKeyId, setRevokingKeyId] = useState<string | null>(null);
  const sessionFingerprint = useMemo(
    () => `${apiBaseUrl}::${bearerToken ?? "public"}`,
    [apiBaseUrl, bearerToken]
  );
  const activeSessionFingerprintRef = useRef(sessionFingerprint);
  activeSessionFingerprintRef.current = sessionFingerprint;

  useEffect(() => {
    setDraftApiBaseUrl(apiBaseUrl);
    setDraftBearerToken(bearerToken ?? "");
  }, [apiBaseUrl, bearerToken]);

  useEffect(() => {
    let isCancelled = false;
    setCreatedSecret(null);
    setIsCreatingKey(false);
    setRevokingKeyId(null);

    if (!bearerToken) {
      setOwnedKeys([]);
      setKeysStatus("idle");
      setKeysError(null);
      setIsCreatingKey(false);
      return () => {
        isCancelled = true;
      };
    }

    setOwnedKeys([]);
    setKeysStatus("loading");
    setKeysError(null);

    void fetchOwnedApiKeys(bearerToken, fetch, { apiBaseUrl })
      .then((response) => {
        if (isCancelled || activeSessionFingerprintRef.current !== sessionFingerprint) {
          return;
        }
        setOwnedKeys(response.items);
        setKeysStatus("ready");
      })
      .catch((error: unknown) => {
        if (isCancelled || activeSessionFingerprintRef.current !== sessionFingerprint) {
          return;
        }
        setOwnedKeys([]);
        setKeysError(getApiKeyErrorMessage(error));
        setKeysStatus("ready");
      });

    return () => {
      isCancelled = true;
    };
  }, [apiBaseUrl, bearerToken, sessionFingerprint]);

  async function handleCreateKey() {
    if (!bearerToken) {
      return;
    }

    const requestFingerprint = sessionFingerprint;
    setCreatedSecret(null);
    setIsCreatingKey(true);
    setKeysError(null);

    try {
      const created = await createOwnedApiKey(bearerToken, fetch, { apiBaseUrl });
      if (activeSessionFingerprintRef.current !== requestFingerprint) {
        return;
      }
      setCreatedSecret(created.api_key);
      setOwnedKeys((currentKeys) => mergeOwnedApiKeys(currentKeys, created.summary));
    } catch (error) {
      if (activeSessionFingerprintRef.current !== requestFingerprint) {
        return;
      }
      setKeysError(getApiKeyErrorMessage(error));
    } finally {
      if (activeSessionFingerprintRef.current === requestFingerprint) {
        setIsCreatingKey(false);
      }
    }
  }

  async function handleRevokeKey(keyId: string) {
    if (!bearerToken) {
      return;
    }

    const requestFingerprint = sessionFingerprint;
    setRevokingKeyId(keyId);
    setKeysError(null);

    try {
      const revoked = await revokeOwnedApiKey(keyId, bearerToken, fetch, { apiBaseUrl });
      if (activeSessionFingerprintRef.current !== requestFingerprint) {
        return;
      }
      setOwnedKeys((currentKeys) =>
        currentKeys.map((key) => (key.key_id === revoked.key_id ? revoked : key))
      );
    } catch (error) {
      if (activeSessionFingerprintRef.current !== requestFingerprint) {
        return;
      }
      setKeysError(getApiKeyErrorMessage(error));
    } finally {
      if (activeSessionFingerprintRef.current === requestFingerprint) {
        setRevokingKeyId(null);
      }
    }
  }

  return (
    <section className="panel config-panel" aria-labelledby="session-config-heading">
      <div className="panel-section">
        <h2 id="session-config-heading">Browser Session</h2>
        <p>
          Public pages stay available without auth. Authenticated pages will reuse
          the stored token later.
        </p>
      </div>
      <form
        className="session-form"
        onSubmit={(event) => {
          event.preventDefault();
          setSession({
            apiBaseUrl: draftApiBaseUrl,
            bearerToken: draftBearerToken
          });
          setSavedMessage("Saved browser session for future authenticated flows.");
        }}
      >
        <label className="field">
          <span>API base URL</span>
          <input
            name="apiBaseUrl"
            type="url"
            value={draftApiBaseUrl}
            onChange={(event) => {
              setDraftApiBaseUrl(event.target.value);
              setSavedMessage("");
            }}
          />
        </label>
        <label className="field">
          <span>Optional human bearer token</span>
          <textarea
            name="bearerToken"
            rows={4}
            value={draftBearerToken}
            onChange={(event) => {
              setDraftBearerToken(event.target.value);
              setSavedMessage("");
            }}
          />
        </label>
        <div className="actions">
          <button className="button-link" type="submit">
            Save session
          </button>
        </div>
        {savedMessage ? (
          <p aria-live="polite" className="helper-text">
            {savedMessage}
          </p>
        ) : null}
      </form>
      <div className="panel-section" aria-labelledby="account-api-keys-heading">
        <h3 id="account-api-keys-heading">Account API Keys</h3>
        {bearerToken ? (
          <p>
            Manage BYOA agent keys with the current browser bearer token. Secrets are shown only
            once when a new key is created.
          </p>
        ) : (
          <p>Add a human bearer token above for owned API key management.</p>
        )}
        {bearerToken ? (
          <div className="actions">
            <button
              className="button-link secondary"
              type="button"
              onClick={() => {
                void handleCreateKey();
              }}
              disabled={keysStatus === "loading" || isCreatingKey || revokingKeyId !== null}
            >
              {isCreatingKey ? "Creating key…" : "Create API key"}
            </button>
          </div>
        ) : null}
        {createdSecret ? (
          <section className="panel state-card" role="status" aria-live="polite">
            <strong>New API key</strong>
            <p>This secret will not be shown again after this response. Store it before you leave this page.</p>
            <code>{createdSecret}</code>
            <div className="actions">
              <button className="button-link secondary" type="button" onClick={() => setCreatedSecret(null)}>
                Dismiss secret
              </button>
            </div>
          </section>
        ) : null}
        {keysError ? (
          <p aria-live="polite" className="helper-text">
            {keysError}
          </p>
        ) : null}
        {bearerToken && keysStatus === "loading" ? <p>Loading owned keys…</p> : null}
        {bearerToken && keysStatus === "ready" ? (
          ownedKeys.length > 0 ? (
            <div className="panel-grid" role="list" aria-label="Owned API keys">
              {ownedKeys.map((key) => (
                <article key={key.key_id} className="panel state-card" role="listitem">
                  <dl className="panel-grid">
                    <div className="metadata-row">
                      <dt>Key id</dt>
                      <dd>{key.key_id}</dd>
                    </div>
                    <div className="metadata-row">
                      <dt>Status</dt>
                      <dd>{key.is_active ? "Active" : "Inactive"}</dd>
                    </div>
                    <div className="metadata-row">
                      <dt>ELO</dt>
                      <dd>{key.elo_rating}</dd>
                    </div>
                    <div className="metadata-row">
                      <dt>Created</dt>
                      <dd>{formatOwnedKeyCreatedAt(key.created_at)}</dd>
                    </div>
                  </dl>
                  <div className="actions">
                    <button
                      className="button-link secondary"
                      type="button"
                      onClick={() => {
                        void handleRevokeKey(key.key_id);
                      }}
                      disabled={!key.is_active || isCreatingKey || revokingKeyId !== null}
                      aria-label={`Revoke ${key.key_id}`}
                    >
                      {revokingKeyId === key.key_id ? "Revoking…" : "Revoke"}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p>No owned API keys yet.</p>
          )
        ) : null}
      </div>
    </section>
  );
}

function getApiKeyErrorMessage(error: unknown): string {
  return error instanceof ApiKeyLifecycleError ? error.message : API_KEY_ERROR_FALLBACK_MESSAGE;
}

function mergeOwnedApiKeys(currentKeys: OwnedApiKeySummary[], nextKey: OwnedApiKeySummary): OwnedApiKeySummary[] {
  const remainingKeys = currentKeys.filter((key) => key.key_id !== nextKey.key_id);
  return [...remainingKeys, nextKey].sort((left, right) => left.created_at.localeCompare(right.created_at));
}

function formatOwnedKeyCreatedAt(value: string): string {
  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return `${parsed.getUTCFullYear()}-${padUtcPart(parsed.getUTCMonth() + 1)}-${padUtcPart(parsed.getUTCDate())} ${padUtcPart(parsed.getUTCHours())}:${padUtcPart(parsed.getUTCMinutes())}:${padUtcPart(parsed.getUTCSeconds())} UTC`;
}

function padUtcPart(value: number): string {
  return String(value).padStart(2, "0");
}
