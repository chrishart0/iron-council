import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { MatchLiveView } from "./match-live-view";

afterEach(() => {
  cleanup();
});

describe("MatchLiveView", () => {
  it("renders the spectator live snapshot as text-first public state", () => {
    render(
      <MatchLiveView
        envelope={{
          type: "tick_update",
          data: {
            match_id: "match-alpha",
            viewer_role: "spectator",
            player_id: null,
            state: {
              match_id: "match-alpha",
              tick: 143,
              cities: {
                birmingham: {
                  owner: "player-1",
                  population: 12,
                  resources: {
                    food: 3,
                    production: 2,
                    money: 8
                  },
                  upgrades: {
                    economy: 2,
                    military: 1,
                    fortification: 0
                  },
                  garrison: 7,
                  building_queue: []
                }
              },
              armies: [
                {
                  id: "army-1",
                  owner: "player-2",
                  troops: 5,
                  location: "manchester",
                  destination: null,
                  path: null,
                  ticks_remaining: 0
                }
              ],
              players: {
                "player-1": {
                  resources: {
                    food: 120,
                    production: 85,
                    money: 200
                  },
                  cities_owned: ["birmingham"],
                  alliance_id: null,
                  is_eliminated: false
                }
              },
              victory: {
                leading_alliance: null,
                cities_held: 1,
                threshold: 13,
                countdown_ticks_remaining: null
              }
            },
            world_messages: [
              {
                message_id: 2,
                channel: "world",
                sender_id: "player-1",
                recipient_id: null,
                tick: 143,
                content: "War drums."
              }
            ],
            direct_messages: [],
            group_chats: [],
            group_messages: [],
            treaties: [],
            alliances: []
          }
        }}
        liveStatus="live"
      />
    );

    expect(screen.getByRole("heading", { name: "Live spectator state" })).toBeVisible();
    expect(screen.getByText("Live")).toBeVisible();
    const summary = screen.getByLabelText("Live spectator summary");
    expect(within(summary).getByText("143")).toBeVisible();
    expect(within(summary).getAllByText("1").length).toBeGreaterThan(0);
    expect(screen.getByText("War drums.")).toBeVisible();
    expect(screen.getByText("player-2")).toBeVisible();
    expect(screen.getByText("manchester")).toBeVisible();
  });
});
