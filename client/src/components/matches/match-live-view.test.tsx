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
            treaties: [
              {
                treaty_id: 7,
                player_a_id: "player-1",
                player_b_id: "player-9",
                treaty_type: "trade",
                status: "active",
                proposed_by: "player-1",
                proposed_tick: 140,
                signed_tick: 141,
                withdrawn_by: null,
                withdrawn_tick: null
              }
            ],
            alliances: [
              {
                alliance_id: "alliance-red",
                name: "Western Accord",
                leader_id: "player-1",
                formed_tick: 120,
                members: [
                  { player_id: "player-1", joined_tick: 120 },
                  { player_id: "player-9", joined_tick: 121 }
                ]
              }
            ]
          }
        }}
        roster={[
          { player_id: "player-1", display_name: "Arthur", competitor_kind: "human" },
          { player_id: "player-2", display_name: "Morgana", competitor_kind: "agent" }
        ]}
        liveStatus="live"
      />
    );

    expect(screen.getByRole("heading", { name: "Live spectator state" })).toBeVisible();
    expect(screen.getByText("Live")).toBeVisible();
    const summary = screen.getByLabelText("Live spectator summary");
    expect(within(summary).getByText("143")).toBeVisible();
    expect(within(summary).getAllByText("1").length).toBeGreaterThan(0);
    expect(screen.getByText("Arthur: War drums.")).toBeVisible();
    expect(screen.getByText("player-2")).toBeVisible();
    expect(screen.getByText("manchester")).toBeVisible();
    expect(screen.getByText("Arthur and player-9 • trade • active")).toBeVisible();
    expect(screen.getByText("Western Accord: Arthur, player-9")).toBeVisible();
  });

  it("renders explicit empty states for text-first situation-room panels", () => {
    render(
      <MatchLiveView
        envelope={{
          type: "tick_update",
          data: {
            match_id: "match-empty",
            viewer_role: "spectator",
            player_id: null,
            state: {
              match_id: "match-empty",
              tick: 1,
              cities: {},
              armies: [],
              players: {},
              victory: {
                leading_alliance: null,
                cities_held: 0,
                threshold: 13,
                countdown_ticks_remaining: null
              }
            },
            world_messages: [],
            direct_messages: [],
            group_chats: [],
            group_messages: [],
            treaties: [],
            alliances: []
          }
        }}
        roster={[]}
        liveStatus="live"
      />
    );

    expect(screen.getByText("No public world chat has been broadcast yet.")).toBeVisible();
    expect(screen.getByText("No public treaties are active right now.")).toBeVisible();
    expect(screen.getByText("No public alliances are visible right now.")).toBeVisible();
  });
});
