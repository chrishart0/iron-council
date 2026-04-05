import { screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  MockWebSocket,
  renderPublicMatchLivePage,
  stubSpectatorFetch
} from "./public-match-live-page-test-helpers";
import { makeEnvelope } from "./public-match-live-page-fixtures";

describe("PublicMatchLivePage summary and live-state rendering", () => {
  it("renders the initial spectator payload and deterministic tick updates", async () => {
    stubSpectatorFetch();

    renderPublicMatchLivePage();

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitOpen();
    socket?.emitMessage(makeEnvelope(143));

    await waitFor(() => {
      expect(screen.getByText("143")).toBeVisible();
    });

    expect(screen.getByText("Arthur: War drums.")).toBeVisible();
    expect(screen.getByText("manchester")).toBeVisible();
    const initialMapRegion = screen.getByRole("region", { name: "Britain strategic map" });
    expect(within(initialMapRegion).getByText("Tick 143")).toBeVisible();
    expect(within(initialMapRegion).getByText("Birmingham")).toBeVisible();
    expect(within(initialMapRegion).getByText("Arthur")).toBeVisible();
    expect(within(initialMapRegion).getByText("Garrison 7")).toBeVisible();
    expect(within(initialMapRegion).getByText("Morgana army 5 at Manchester")).toBeVisible();
    expect(screen.getByText("Arthur and player-9 • trade • active")).toBeVisible();
    expect(screen.getByText("Western Accord: Arthur, player-9")).toBeVisible();

    socket?.emitMessage(makeEnvelope(144));

    await waitFor(() => {
      expect(screen.getByText("144")).toBeVisible();
    });

    expect(screen.getByText("Arthur: Advance at dawn.")).toBeVisible();
    expect(screen.getByText("leeds")).toBeVisible();
    const updatedMapRegion = screen.getByRole("region", { name: "Britain strategic map" });
    expect(within(updatedMapRegion).getByText("Tick 144")).toBeVisible();
  });
});
