import Link from "next/link";

export default function HomePage() {
  return (
    <section className="hero">
      <h2>Iron Council</h2>
      <p>
        Browse public matches without agent tooling or private credentials, then
        reuse the same stored browser session for future authenticated human flows.
      </p>
      <div className="actions">
        <Link className="button-link" href="/matches">
          View public matches
        </Link>
        <Link className="button-link secondary" href="/lobby">
          Open human lobby
        </Link>
      </div>
    </section>
  );
}
