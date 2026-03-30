"use client";

import Link from "next/link";
import { useSession } from "../session/session-provider";
import { SessionConfigPanel } from "../session/session-config-panel";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { apiBaseUrl, authStatusLabel } = useSession();

  return (
    <div className="shell app-shell">
      <header className="panel site-header">
        <div>
          <p className="eyebrow">Iron Council Client</p>
          <h1>Human Session Bootstrap</h1>
        </div>
        <nav className="nav-links" aria-label="Primary">
          <Link href="/">Home</Link>
          <Link href="/matches">Public matches</Link>
          <Link href="/lobby">Human lobby (auth required)</Link>
        </nav>
        <dl className="session-summary">
          <div>
            <dt>API</dt>
            <dd>{apiBaseUrl}</dd>
          </div>
          <div>
            <dt>Auth</dt>
            <dd>{authStatusLabel}</dd>
          </div>
        </dl>
      </header>
      <div className="app-shell-body">
        <div className="app-shell-main">{children}</div>
        <aside className="app-shell-sidebar">
          <SessionConfigPanel />
        </aside>
      </div>
    </div>
  );
}
