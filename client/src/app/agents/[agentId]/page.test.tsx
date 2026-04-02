import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import AgentProfileRoutePage from "./page";

vi.mock("../../../components/public/public-agent-profile-page", () => ({
  PublicAgentProfilePage: ({ agentId }: { agentId: string }) => <div>{`profile:${agentId}`}</div>
}));

describe("AgentProfileRoutePage", () => {
  it("passes the dynamic agent id through to the public profile page", async () => {
    render(
      await AgentProfileRoutePage({
        params: Promise.resolve({
          agentId: "agent-player-2"
        })
      })
    );

    expect(screen.getByText("profile:agent-player-2")).toBeVisible();
  });
});
