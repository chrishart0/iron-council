export function makeRosterRow(
  playerId: string,
  displayName: string,
  competitorKind: "human" | "agent"
) {
  return {
    player_id: playerId,
    display_name: displayName,
    competitor_kind: competitorKind,
    agent_id: competitorKind === "agent" ? `agent-${playerId}` : null,
    human_id: competitorKind === "human" ? `human:${playerId}` : null
  };
}

export function makeMatchSummary(options?: {
  status?: "active" | "paused";
  tick?: number;
  currentPlayerCount?: number;
  maxPlayerCount?: number;
  openSlotCount?: number;
  roster?: ReturnType<typeof makeRosterRow>[];
}) {
  return {
    match_id: "match-alpha",
    status: options?.status ?? "active",
    map: "britain",
    tick: options?.tick ?? 142,
    tick_interval_seconds: 30,
    current_player_count: options?.currentPlayerCount ?? 3,
    max_player_count: options?.maxPlayerCount ?? 5,
    open_slot_count: options?.openSlotCount ?? 2,
    roster:
      options?.roster ?? [
        makeRosterRow("player-1", "Arthur", "human"),
        makeRosterRow("player-2", "Morgana", "agent")
      ]
  };
}

export const makeMatchSummaryResponse = makeMatchSummary;

export function makeEnvelope(tick: number) {
  return {
    type: "tick_update",
    data: {
      match_id: "match-alpha",
      viewer_role: "spectator" as const,
      player_id: null,
      state: {
        match_id: "match-alpha",
        tick,
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
            location: tick === 143 ? "manchester" : "leeds",
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
          message_id: tick,
          channel: "world" as const,
          sender_id: "player-1",
          recipient_id: null,
          tick,
          content: tick === 143 ? "War drums." : "Advance at dawn."
        }
      ],
      direct_messages: [],
      group_chats: [],
      group_messages: [],
      treaties: [
        {
          treaty_id: tick,
          player_a_id: "player-1",
          player_b_id: "player-9",
          treaty_type: "trade",
          status: "active",
          proposed_by: "player-1",
          proposed_tick: tick - 2,
          signed_tick: tick - 1,
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
  };
}

export function makePressureEnvelope() {
  return {
    type: "tick_update",
    data: {
      match_id: "match-alpha",
      viewer_role: "spectator" as const,
      player_id: null,
      state: {
        match_id: "match-alpha",
        tick: 201,
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
            owner: "player-9",
            population: 12,
            resources: { food: 3, production: 2, money: 8 },
            upgrades: { economy: 2, military: 1, fortification: 0 },
            garrison: 7,
            building_queue: []
          },
          leeds: {
            owner: "player-2",
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
            resources: { food: 120, production: 85, money: 200 },
            cities_owned: ["london"],
            alliance_id: "alliance-red",
            is_eliminated: false
          },
          "player-2": {
            resources: { food: 120, production: 85, money: 200 },
            cities_owned: ["leeds"],
            alliance_id: null,
            is_eliminated: false
          },
          "player-9": {
            resources: { food: 120, production: 85, money: 200 },
            cities_owned: ["york"],
            alliance_id: "alliance-red",
            is_eliminated: false
          }
        },
        victory: {
          leading_alliance: "alliance-red",
          cities_held: 2,
          threshold: 13,
          countdown_ticks_remaining: 4
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
            { player_id: "player-9", joined_tick: 121 }
          ]
        }
      ]
    }
  };
}

export function makeTransitEnvelope() {
  return {
    type: "tick_update",
    data: {
      match_id: "match-alpha",
      viewer_role: "spectator" as const,
      player_id: null,
      state: {
        match_id: "match-alpha",
        tick: 143,
        cities: {
          manchester: {
            owner: "player-1",
            population: 12,
            resources: { food: 3, production: 2, money: 8 },
            upgrades: { economy: 2, military: 1, fortification: 0 },
            garrison: 7,
            building_queue: []
          },
          leeds: {
            owner: "player-1",
            population: 12,
            resources: { food: 3, production: 2, money: 8 },
            upgrades: { economy: 2, military: 1, fortification: 0 },
            garrison: 3,
            building_queue: []
          }
        },
        armies: [
          {
            id: "army-transit",
            owner: "player-1",
            troops: 9,
            location: "manchester",
            destination: "leeds",
            path: ["manchester", "leeds"],
            ticks_remaining: 3
          }
        ],
        players: {
          "player-1": {
            resources: { food: 120, production: 85, money: 200 },
            cities_owned: ["manchester", "leeds"],
            alliance_id: null,
            is_eliminated: false
          }
        },
        victory: {
          leading_alliance: null,
          cities_held: 2,
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
  };
}

export function makeCollisionEnvelope() {
  return {
    type: "tick_update",
    data: {
      match_id: "match-alpha",
      viewer_role: "spectator" as const,
      player_id: null,
      state: {
        match_id: "match-alpha",
        tick: 202,
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
            resources: { food: 120, production: 85, money: 200 },
            cities_owned: ["london"],
            alliance_id: null,
            is_eliminated: false
          },
          "player-2": {
            resources: { food: 120, production: 85, money: 200 },
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
  };
}
