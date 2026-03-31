import { ProtectedRoute } from "../../components/navigation/protected-route";
import { HumanLobbyPage } from "../../components/lobby/human-lobby-page";

export default function LobbyPage() {
  return (
    <ProtectedRoute title="Human lobby">
      <HumanLobbyPage />
    </ProtectedRoute>
  );
}
