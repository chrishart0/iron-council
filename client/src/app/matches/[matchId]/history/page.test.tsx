import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import MatchHistoryPage from "./page";

const { mockMatchHistoryPage } = vi.hoisted(() => ({
  mockMatchHistoryPage: vi.fn(
    ({ matchId, selectedTick }: { matchId: string; selectedTick: number | null }) => (
      <div>{`${matchId}:${selectedTick === null ? "null" : selectedTick}`}</div>
    )
  )
}));

vi.mock("../../../../components/public/match-history-page", () => ({
  MatchHistoryPage: mockMatchHistoryPage
}));

describe("MatchHistoryPage", () => {
  it("passes the route match id and parsed tick query to the client history page", async () => {
    render(
      await MatchHistoryPage({
        params: Promise.resolve({
          matchId: "match-complete"
        }),
        searchParams: Promise.resolve({
          tick: "155"
        })
      })
    );

    expect(screen.getByText("match-complete:155")).toBeVisible();
    expect(mockMatchHistoryPage).toHaveBeenCalledWith(
      {
        matchId: "match-complete",
        selectedTick: 155
      },
      undefined
    );
  });

  it("falls back to the latest persisted tick when the query parameter is missing or invalid", async () => {
    render(
      await MatchHistoryPage({
        params: Promise.resolve({
          matchId: "match-complete"
        }),
        searchParams: Promise.resolve({
          tick: "not-a-number"
        })
      })
    );

    expect(screen.getByText("match-complete:null")).toBeVisible();
  });
});
