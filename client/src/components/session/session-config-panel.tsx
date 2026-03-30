"use client";

import { useEffect, useState } from "react";
import { useSession } from "./session-provider";

export function SessionConfigPanel() {
  const { apiBaseUrl, bearerToken, setSession } = useSession();
  const [draftApiBaseUrl, setDraftApiBaseUrl] = useState(apiBaseUrl);
  const [draftBearerToken, setDraftBearerToken] = useState(bearerToken ?? "");
  const [savedMessage, setSavedMessage] = useState("");

  useEffect(() => {
    setDraftApiBaseUrl(apiBaseUrl);
    setDraftBearerToken(bearerToken ?? "");
  }, [apiBaseUrl, bearerToken]);

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
    </section>
  );
}
