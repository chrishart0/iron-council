"use client";

import Link from "next/link";
import { useSession } from "../session/session-provider";

export function ProtectedRoute({
  children,
  title
}: {
  children: React.ReactNode;
  title: string;
}) {
  const { hasHydrated, isAuthenticated } = useSession();

  if (!hasHydrated) {
    return (
      <section className="panel state-card" aria-live="polite" aria-busy="true">
        <strong>{title}</strong>
        <p>Loading the stored browser session.</p>
      </section>
    );
  }

  if (isAuthenticated) {
    return <>{children}</>;
  }

  return (
    <section className="panel state-card">
      <strong>{title}</strong>
      <p>
        This route requires a configured human bearer token before later lobby and
        gameplay flows can open.
      </p>
      <p>
        Save a token in the browser session panel, then revisit this route.
        Public pages remain available in the meantime.
      </p>
      <div className="actions">
        <Link className="button-link secondary" href="/">
          Return to public pages
        </Link>
      </div>
    </section>
  );
}
