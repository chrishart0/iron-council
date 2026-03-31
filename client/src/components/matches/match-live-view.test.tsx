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
    const territoryPressureSection = screen
      .getByRole("heading", { name: "Territory pressure" })
      .closest("section");
    const victoryContextSection = screen
      .getByRole("heading", { name: "Victory context" })
      .closest("section");

    expect(territoryPressureSection).not.toBeNull();
    expect(victoryContextSection).not.toBeNull();
    expect(
      within(territoryPressureSection as HTMLElement).getByText(
        "No owned cities are visible in the current spectator update yet."
      )
    ).toBeVisible();
    expect(
      within(victoryContextSection as HTMLElement).getByText(
        "No owned cities are visible in the current spectator update yet."
      )
    ).toBeVisible();
    expect(
      within(victoryContextSection as HTMLElement).getByText(
        "No coalition is currently on a victory countdown."
      )
    ).toBeVisible();
  });

  it("renders deterministic territory pressure summaries and active victory context", () => {
    render(
      <MatchLiveView
        envelope={{
          type: "tick_update",
          data: {
            match_id: "match-pressure",
            viewer_role: "spectator",
            player_id: null,
            state: {
              match_id: "match-pressure",
              tick: 212,
              cities: {
                london: {
                  owner: "player-1",
                  population: 12,
                  resources: { food: 3, production: 2, money: 8 },
                  upgrades: { economy: 2, military: 1, fortification: 0 },
                  garrison: 7,
                  building_queue: []
                },
                york: {
                  owner: "player-2",
                  population: 10,
                  resources: { food: 3, production: 2, money: 8 },
                  upgrades: { economy: 2, military: 1, fortification: 0 },
                  garrison: 7,
                  building_queue: []
                },
                leeds: {
                  owner: "player-3",
                  population: 10,
                  resources: { food: 3, production: 2, money: 8 },
                  upgrades: { economy: 2, military: 1, fortification: 0 },
                  garrison: 7,
                  building_queue: []
                },
                bath: {
                  owner: "player-4",
                  population: 10,
                  resources: { food: 3, production: 2, money: 8 },
                  upgrades: { economy: 2, military: 1, fortification: 0 },
                  garrison: 7,
                  building_queue: []
                }
              },
              armies: [],
              players: {
                "player-1": {
                  resources: { food: 100, production: 100, money: 100 },
                  cities_owned: ["london"],
                  alliance_id: "alliance-red",
                  is_eliminated: false
                },
                "player-2": {
                  resources: { food: 100, production: 100, money: 100 },
                  cities_owned: ["york"],
                  alliance_id: "alliance-red",
                  is_eliminated: false
                },
                "player-3": {
                  resources: { food: 100, production: 100, money: 100 },
                  cities_owned: ["leeds"],
                  alliance_id: null,
                  is_eliminated: false
                },
                "player-4": {
                  resources: { food: 100, production: 100, money: 100 },
                  cities_owned: ["bath"],
                  alliance_id: null,
                  is_eliminated: false
                }
              },
              victory: {
                leading_alliance: "alliance-red",
                cities_held: 2,
                threshold: 13,
                countdown_ticks_remaining: 5
              }
            },
            world_messages: [],
            direct_messages: [],
            group_chats: [],
            group_messages: [],
            treaties: [],
            alliances: [
              {
                alliance_id: "alliance-red",
                name: "Western Accord",
                leader_id: "player-1",
                formed_tick: 120,
                members: [
                  { player_id: "player-1", joined_tick: 120 },
                  { player_id: "player-2", joined_tick: 121 }
                ]
              }
            ]
          }
        }}
        roster={[
          { player_id: "player-1", display_name: "Arthur", competitor_kind: "human" },
          { player_id: "player-2", display_name: "Beatrice", competitor_kind: "human" },
          { player_id: "player-3", display_name: "Cedric", competitor_kind: "agent" },
          { player_id: "player-4", display_name: "Alfred", competitor_kind: "agent" }
        ]}
        liveStatus="live"
      />
    );

    const pressureBoard = screen.getByLabelText("Territory pressure");
    const pressureRows = within(pressureBoard).getAllByRole("listitem");
    expect(pressureRows).toHaveLength(3);
    expect(pressureRows[0]).toHaveTextContent("Western Accord");
    expect(pressureRows[0]).toHaveTextContent("2 cities");
    expect(pressureRows[1]).toHaveTextContent("Alfred");
    expect(pressureRows[1]).toHaveTextContent("1 city");
    expect(pressureRows[2]).toHaveTextContent("Cedric");
    expect(pressureRows[2]).toHaveTextContent("1 city");

    expect(
      screen.getByText("Western Accord leads the victory race with 2 of 13 cities.")
    ).toBeVisible();
    expect(screen.getByText("Victory countdown: 5 ticks remaining.")).toBeVisible();
  });

  it("keeps unrelated owners separate when display labels collide", () => {
    render(
      <MatchLiveView
        envelope={{
          type: "tick_update",
          data: {
            match_id: "match-collision",
            viewer_role: "spectator",
            player_id: null,
            state: {
              match_id: "match-collision",
              tick: 33,
              cities: {
                london: {
                  owner: "player-1",
                  population: 12,
                  resources: { food: 3, production: 2, money: 8 },
                  upgrades: { economy: 2, military: 1, fortification: 0 },
                  garrison: 7,
                  building_queue: []
                },
                york: {
                  owner: "player-2",
                  population: 10,
                  resources: { food: 3, production: 2, money: 8 },
                  upgrades: { economy: 2, military: 1, fortification: 0 },
                  garrison: 7,
                  building_queue: []
                }
              },
              armies: [],
              players: {
                "player-1": {
                  resources: { food: 100, production: 100, money: 100 },
                  cities_owned: ["london"],
                  alliance_id: null,
                  is_eliminated: false
                },
                "player-2": {
                  resources: { food: 100, production: 100, money: 100 },
                  cities_owned: ["york"],
                  alliance_id: null,
                  is_eliminated: false
                }
              },
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
        roster={[
          { player_id: "player-1", display_name: "Arthur", competitor_kind: "human" },
          { player_id: "player-2", display_name: "Arthur", competitor_kind: "agent" }
        ]}
        liveStatus="live"
      />
    );

    const pressureBoard = screen.getByLabelText("Territory pressure");
    const pressureRows = within(pressureBoard).getAllByRole("listitem");
    expect(pressureRows).toHaveLength(2);
    expect(pressureRows[0]).toHaveTextContent("Arthur");
    expect(pressureRows[0]).toHaveTextContent("1 city");
    expect(pressureRows[1]).toHaveTextContent("Arthur");
    expect(pressureRows[1]).toHaveTextContent("1 city");
  });

  it("renders explanatory victory copy when territory is visible but the race is inactive", () => {
    render(
      <MatchLiveView
        envelope={{
          type: "tick_update",
          data: {
            match_id: "match-inactive",
            viewer_role: "spectator",
            player_id: null,
            state: {
              match_id: "match-inactive",
              tick: 90,
              cities: {
                london: {
                  owner: "player-1",
                  population: 12,
                  resources: { food: 3, production: 2, money: 8 },
                  upgrades: { economy: 2, military: 1, fortification: 0 },
                  garrison: 7,
                  building_queue: []
                }
              },
              armies: [],
              players: {
                "player-1": {
                  resources: { food: 100, production: 100, money: 100 },
                  cities_owned: ["london"],
                  alliance_id: null,
                  is_eliminated: false
                }
              },
              victory: {
                leading_alliance: "alliance-shadow",
                cities_held: 1,
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
        roster={[{ player_id: "player-1", display_name: "Arthur", competitor_kind: "human" }]}
        liveStatus="live"
      />
    );

    const victoryContextSection = screen
      .getByRole("heading", { name: "Victory context" })
      .closest("section");

    expect(victoryContextSection).not.toBeNull();
    expect(
      within(victoryContextSection as HTMLElement).getByText("Arthur holds 1 visible city.")
    ).toBeVisible();
    expect(
      within(victoryContextSection as HTMLElement).getByText(
        "No coalition is currently on a victory countdown."
      )
    ).toBeVisible();
    expect(
      within(victoryContextSection as HTMLElement).queryByText(/leads the victory race/i)
    ).not.toBeInTheDocument();
  });
});
