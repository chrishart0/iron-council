import { describe, expect, it } from "vitest";
import {
  parsePlayerMatchEnvelope,
  parseSpectatorMatchEnvelope,
  parseWebSocketApiErrorEnvelope
} from "./live-envelope";

describe("spectator realtime helpers", () => {
  it("parses a valid spectator tick update envelope", () => {
    expect(
      parseSpectatorMatchEnvelope({
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
      })
    ).toEqual({
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
    });
  });

  it("rejects malformed spectator realtime payloads deterministically", () => {
    expect(() =>
      parseSpectatorMatchEnvelope({
        type: "tick_update",
        data: {
          match_id: "match-alpha",
          viewer_role: "spectator",
          state: {
            tick: "143"
          }
        }
      })
    ).toThrowError("Unable to parse spectator live match update.");
  });
});


describe("player realtime helpers", () => {
  it("parses a valid player tick update envelope", () => {
    expect(
      parsePlayerMatchEnvelope({
        type: "tick_update",
        data: {
          match_id: "match-alpha",
          viewer_role: "player",
          player_id: "player-2",
          state: {
            match_id: "match-alpha",
            tick: 143,
            player_id: "player-2",
            resources: {
              food: 120,
              production: 85,
              money: 200
            },
            cities: {
              manchester: {
                owner: "player-2",
                visibility: "full",
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
              },
              birmingham: {
                owner: "player-3",
                visibility: "partial",
                population: "unknown",
                resources: "unknown",
                upgrades: "unknown",
                garrison: "unknown",
                building_queue: "unknown"
              }
            },
            visible_armies: [
              {
                id: "army-1",
                owner: "player-2",
                visibility: "full",
                troops: 5,
                location: "manchester",
                destination: null,
                path: null,
                ticks_remaining: 0
              },
              {
                id: "army-2",
                owner: "player-3",
                visibility: "partial",
                troops: "unknown",
                location: null,
                destination: "birmingham",
                path: "unknown",
                ticks_remaining: 2
              }
            ],
            alliance_id: "alliance-red",
            alliance_members: ["player-1", "player-2"],
            victory: {
              leading_alliance: "alliance-red",
              cities_held: 9,
              threshold: 13,
              countdown_ticks_remaining: 4
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
          direct_messages: [
            {
              message_id: 3,
              channel: "direct",
              sender_id: "player-1",
              recipient_id: "player-2",
              tick: 143,
              content: "Hold the line."
            }
          ],
          group_chats: [
            {
              group_chat_id: "council-red",
              name: "Red Council",
              member_ids: ["player-1", "player-2"],
              created_by: "player-1",
              created_tick: 140
            }
          ],
          group_messages: [
            {
              message_id: 4,
              group_chat_id: "council-red",
              sender_id: "player-2",
              tick: 143,
              content: "Ready."
            }
          ],
          treaties: [
            {
              treaty_id: 5,
              player_a_id: "player-1",
              player_b_id: "player-2",
              treaty_type: "alliance",
              status: "accepted",
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
              name: "alliance-red",
              leader_id: "player-1",
              formed_tick: 140,
              members: [
                { player_id: "player-1", joined_tick: 140 },
                { player_id: "player-2", joined_tick: 140 }
              ]
            }
          ]
        }
      })
    ).toMatchObject({
      type: "tick_update",
      data: {
        viewer_role: "player",
        player_id: "player-2",
        state: {
          player_id: "player-2",
          cities: {
            birmingham: {
              visibility: "partial",
              garrison: "unknown"
            }
          },
          visible_armies: [
            { id: "army-1", visibility: "full", troops: 5 },
            { id: "army-2", visibility: "partial", troops: "unknown", path: "unknown" }
          ],
          alliance_members: ["player-1", "player-2"]
        },
        direct_messages: [{ content: "Hold the line." }],
        group_chats: [{ name: "Red Council" }],
        treaties: [{ status: "accepted" }],
        alliances: [{ alliance_id: "alliance-red" }]
      }
    });
  });

  it("rejects malformed player realtime payloads deterministically", () => {
    expect(() =>
      parsePlayerMatchEnvelope({
        type: "tick_update",
        data: {
          match_id: "match-alpha",
          viewer_role: "player",
          player_id: "player-2",
          state: {
            tick: "143"
          }
        }
      })
    ).toThrowError("Unable to parse player live match update.");
  });

  it("parses a structured websocket api error envelope for auth failures", () => {
    expect(
      parseWebSocketApiErrorEnvelope({
        error: {
          code: "invalid_websocket_auth",
          message: "Player websocket connections require a valid human JWT token query parameter."
        }
      })
    ).toEqual({
      error: {
        code: "invalid_websocket_auth",
        message: "Player websocket connections require a valid human JWT token query parameter."
      }
    });
  });
});
