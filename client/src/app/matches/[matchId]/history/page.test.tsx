import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import MatchHistoryPage from "./page";

describe("MatchHistoryPage", () => {
  it("renders a lightweight history landing surface for the completed-match route", async () => {
    render(
      await MatchHistoryPage({
        params: Promise.resolve({
          matchId: "match-complete"
        })
      })
    );

    expect(screen.getByRole("heading", { name: "Match History" })).toBeVisible();
    expect(screen.getByText("match-complete")).toBeVisible();
    expect(
      screen.getByText(
        "Persisted replay inspection and tick-by-tick browsing ship in the next public replay story."
      )
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "Back to completed matches" })).toHaveAttribute(
      "href",
      "/matches/completed"
    );
    expect(screen.getByRole("link", { name: "View leaderboard" })).toHaveAttribute(
      "href",
      "/leaderboard"
    );
    expect(screen.getByRole("link", { name: "Back to home" })).toHaveAttribute("href", "/");
  });
});
