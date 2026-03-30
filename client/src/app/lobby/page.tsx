import { ProtectedRoute } from "../../components/navigation/protected-route";

export default function LobbyPage() {
  return (
    <ProtectedRoute title="Human lobby">
      <section className="hero">
        <h2>Authenticated Lobby Placeholder</h2>
        <p>
          This placeholder route is reserved for later human lobby and gameplay
          stories. It already reuses the shared browser session shell.
        </p>
      </section>
    </ProtectedRoute>
  );
}
