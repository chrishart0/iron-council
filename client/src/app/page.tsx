import Link from "next/link";

export default function HomePage() {
  return (
    <main className="shell">
      <section className="hero">
        <h1>Iron Council</h1>
        <p>
          Browse public matches without agent tooling or private credentials.
        </p>
        <div className="actions">
          <Link className="button-link" href="/matches">
            View public matches
          </Link>
        </div>
      </section>
    </main>
  );
}
