import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { MatchBrowser } from "./match-browser";

afterEach(() => {
  cleanup();
});

describe("MatchBrowser", () => {
  it("renders compact public browse metadata for each match", () => {
    render(
      <MatchBrowser
        matches={[
          {
            match_id: "match-alpha",
            status: "active",
            map: "britain",
            tick: 142,
            tick_interval_seconds: 30,
            current_player_count: 3,
            max_player_count: 5,
            open_slot_count: 2
          }
        ]}
      />
    );

    const table = screen.getByRole("table");
    const row = within(table).getByRole("row", { name: /match-alpha/i });

    expect(row).toHaveTextContent("match-alpha");
    expect(row).toHaveTextContent("active");
    expect(row).toHaveTextContent("britain");
    expect(row).toHaveTextContent("142");
    expect(row).toHaveTextContent("30s");
    expect(row).toHaveTextContent("3");
    expect(row).toHaveTextContent("5");
    expect(row).toHaveTextContent("2");
  });

  it("links each public browse row to the read-only detail page", () => {
    render(
      <MatchBrowser
        matches={[
          {
            match_id: "match-alpha",
            status: "active",
            map: "britain",
            tick: 142,
            tick_interval_seconds: 30,
            current_player_count: 3,
            max_player_count: 5,
            open_slot_count: 2
          }
        ]}
      />
    );

    expect(screen.getByRole("link", { name: /view details for match-alpha/i })).toHaveAttribute(
      "href",
      "/matches/match-alpha"
    );
  });

  it("renders a deterministic empty state when no public matches exist", () => {
    render(<MatchBrowser matches={[]} />);

    expect(screen.getByRole("status")).toHaveTextContent(
      "No public matches yet"
    );
    expect(screen.getByText(/start the server or create a lobby/i)).toBeVisible();
  });

  it("renders a deterministic error state without raw transport details", () => {
    render(
      <MatchBrowser errorMessage="Unable to load public matches right now." />
    );

    expect(screen.getByRole("status")).toHaveTextContent("Matches unavailable");
    expect(
      screen.getByText("Unable to load public matches right now.")
    ).toBeVisible();
  });
});
