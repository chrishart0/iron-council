export default function MatchesLoadingPage() {
  return (
    <main className="shell">
      <section className="hero">
        <h1>Public Matches</h1>
      </section>
      <section className="panel state-card" aria-live="polite">
        <strong>Loading matches</strong>
        <p>Checking the current public lobby and live game list.</p>
      </section>
    </main>
  );
}
