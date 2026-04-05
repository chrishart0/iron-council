import { screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  MockWebSocket,
  renderPublicMatchLivePage,
  stubSpectatorFetch
} from "./public-match-live-page-test-helpers";
import {
  makeCollisionEnvelope,
  makeMatchSummaryResponse,
  makePressureEnvelope,
  makeRosterRow
} from "./public-match-live-page-fixtures";

describe("PublicMatchLivePage territory pressure and victory context", () => {
  it("renders territory pressure and victory context from the shipped websocket payload", async () => {
    stubSpectatorFetch();

    renderPublicMatchLivePage();

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitOpen();
    socket?.emitMessage(makePressureEnvelope());

    await waitFor(() => {
      expect(screen.getByLabelText("Territory pressure")).toBeVisible();
    });

    const pressureBoard = screen.getByLabelText("Territory pressure");
    const pressureRows = within(pressureBoard).getAllByRole("listitem");
    expect(pressureRows[0]).toHaveTextContent("Western Accord");
    expect(pressureRows[0]).toHaveTextContent("2 cities");
    expect(pressureRows[1]).toHaveTextContent("Morgana");
    expect(pressureRows[1]).toHaveTextContent("1 city");
    expect(screen.getByText("Western Accord leads the victory race with 2 of 13 cities.")).toBeVisible();
    expect(screen.getByText("Victory countdown: 4 ticks remaining.")).toBeVisible();
  });

  it("keeps same-label players separate in the territory pressure section", async () => {
    stubSpectatorFetch(
      makeMatchSummaryResponse({
        currentPlayerCount: 2,
        openSlotCount: 3,
        roster: [
          makeRosterRow("player-1", "Arthur", "human"),
          makeRosterRow("player-2", "Arthur", "agent")
        ]
      })
    );

    renderPublicMatchLivePage();

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitOpen();
    socket?.emitMessage(makeCollisionEnvelope());

    await waitFor(() => {
      expect(screen.getByLabelText("Territory pressure")).toBeVisible();
    });

    const pressureBoard = screen.getByLabelText("Territory pressure");
    const pressureRows = within(pressureBoard).getAllByRole("listitem");
    expect(pressureRows).toHaveLength(2);
    expect(pressureRows[0]).toHaveTextContent("Arthur");
    expect(pressureRows[0]).toHaveTextContent("1 city");
    expect(pressureRows[1]).toHaveTextContent("Arthur");
    expect(pressureRows[1]).toHaveTextContent("1 city");
  });
});
