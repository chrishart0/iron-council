export function makeEnvelope(tick: number) {
  return {
    type: "tick_update",
    data: {
      match_id: "match-alpha",
      viewer_role: "player" as const,
      player_id: "player-2",
      state: {
        match_id: "match-alpha",
        tick,
        player_id: "player-2",
        resources: {
          food: 120 + tick,
          production: 85,
          money: 200
        },
        cities: {
          manchester: {
            owner: "player-2",
            visibility: "full" as const,
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
            visibility: "partial" as const,
            population: "unknown" as const,
            resources: "unknown" as const,
            upgrades: "unknown" as const,
            garrison: "unknown" as const,
            building_queue: "unknown" as const
          }
        },
        visible_armies: [
          {
            id: "army-1",
            owner: "player-2",
            visibility: "full" as const,
            troops: 5,
            location: tick === 144 ? "leeds" : "manchester",
            destination: null,
            path: null,
            ticks_remaining: 0
          },
          {
            id: "army-2",
            owner: "player-3",
            visibility: "partial" as const,
            troops: "unknown" as const,
            location: null,
            destination: "birmingham",
            path: "unknown" as const,
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
          message_id: tick,
          channel: "world" as const,
          sender_id: "player-1",
          recipient_id: null,
          tick,
          content: tick === 144 ? "Advance at dawn." : "War drums."
        }
      ],
      direct_messages: [
        {
          message_id: tick + 100,
          channel: "direct" as const,
          sender_id: "player-1",
          recipient_id: "player-2",
          tick,
          content: tick === 144 ? "Press north." : "Hold the line."
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
          message_id: tick + 200,
          group_chat_id: "council-red",
          sender_id: "player-2",
          tick,
          content: tick === 144 ? "Moving." : "Ready."
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
  };
}

export function makeJoinableAllianceEnvelope(tick: number) {
  const envelope = makeEnvelope(tick);
  return {
    ...envelope,
    data: {
      ...envelope.data,
      state: {
        ...envelope.data.state,
        alliance_id: null,
        alliance_members: []
      },
      alliances: envelope.data.alliances.map((alliance) => ({
        ...alliance,
        members: alliance.members.filter((member) => member.player_id !== envelope.data.player_id)
      }))
    }
  };
}

export function makeSoloVisibleEnvelope(tick: number) {
  const envelope = makeEnvelope(tick);
  return {
    ...envelope,
    data: {
      ...envelope.data,
      world_messages: [],
      direct_messages: [],
      group_chats: [],
      group_messages: [],
      treaties: [],
      alliances: [],
      state: {
        ...envelope.data.state,
        alliance_members: ["player-2"],
        cities: {
          manchester: envelope.data.state.cities.manchester
        },
        visible_armies: [
          {
            id: "army-1",
            owner: "player-2",
            visibility: "full" as const,
            troops: 5,
            location: "manchester",
            destination: null,
            path: null,
            ticks_remaining: 0
          }
        ]
      }
    }
  };
}

export function makeHiddenTransitEnvelope() {
  const envelope = makeEnvelope(143);
  return {
    ...envelope,
    data: {
      ...envelope.data,
      state: {
        ...envelope.data.state,
        visible_armies: [
          {
            id: "army-2",
            owner: "player-3",
            visibility: "partial" as const,
            troops: "unknown" as const,
            location: null,
            destination: "birmingham",
            path: "unknown" as const,
            ticks_remaining: 2
          }
        ]
      }
    }
  };
}

export function makePublicMatchDetailResponse() {
  return {
    match_id: "match-alpha",
    status: "active",
    map: "britain",
    tick: 142,
    tick_interval_seconds: 30,
    current_player_count: 3,
    max_player_count: 5,
    open_slot_count: 2,
    roster: [
      {
        player_id: "player-2",
        display_name: "Agent Two",
        competitor_kind: "agent",
        agent_id: "agent-player-2",
        human_id: null
      }
    ]
  };
}

export function makeHumanOwnedAgentMatchDetailResponse() {
  return {
    match_id: "match-alpha",
    status: "active",
    map: "britain",
    tick: 142,
    tick_interval_seconds: 30,
    current_player_count: 3,
    max_player_count: 5,
    open_slot_count: 2,
    roster: [
      {
        player_id: "player-1",
        display_name: "Arthur",
        competitor_kind: "human",
        agent_id: null,
        human_id: "human:00000000-0000-0000-0000-000000000301"
      },
      {
        player_id: "player-2",
        display_name: "Agent Two",
        competitor_kind: "agent",
        agent_id: "agent-player-2",
        human_id: null
      }
    ]
  };
}

export function makeOwnedApiKeysResponse() {
  return {
    items: [
      {
        key_id: "key-alpha",
        agent_id: "agent-player-2",
        elo_rating: 1210,
        is_active: true,
        created_at: "2026-04-03T09:00:00Z",
        entitlement: {
          is_entitled: true,
          grant_source: "manual",
          concurrent_match_allowance: 1,
          granted_at: "2026-04-03T09:00:00Z"
        }
      }
    ]
  };
}

export function makeGuidedSessionResponse(options?: {
  guidanceContent?: string;
  queuedDestination?: string;
}) {
  return {
    match_id: "match-alpha",
    agent_id: "agent-player-2",
    player_id: "player-2",
    state: {
      match_id: "match-alpha",
      player_id: "player-2",
      tick: 144,
      resources: {
        food: 120,
        production: 80,
        money: 200
      },
      cities: {},
      visible_armies: [],
      alliance_id: "alliance-red",
      alliance_members: ["player-1", "player-2"],
      victory: {
        leading_alliance: "alliance-red",
        cities_held: 9,
        threshold: 13,
        countdown_ticks_remaining: 4
      }
    },
    queued_orders: {
      movements: [{ army_id: "army-1", destination: options?.queuedDestination ?? "york" }],
      recruitment: [],
      upgrades: [],
      transfers: []
    },
    guidance: [
      {
        guidance_id: "guidance-7",
        match_id: "match-alpha",
        player_id: "player-2",
        tick: 144,
        content: options?.guidanceContent ?? "Hold the north.",
        created_at: "2026-04-04T12:00:00Z"
      }
    ],
    group_chats: [],
    messages: {
      world: [],
      direct: [],
      group: []
    },
    recent_activity: {
      alliances: [],
      treaties: []
    }
  };
}

export function makeHumanEnvelope(tick: number) {
  const envelope = makeEnvelope(tick);
  return {
    ...envelope,
    data: {
      ...envelope.data,
      player_id: "player-1",
      state: {
        ...envelope.data.state,
        player_id: "player-1"
      },
      direct_messages: [
        {
          message_id: tick + 100,
          channel: "direct" as const,
          sender_id: "player-2",
          recipient_id: "player-1",
          tick,
          content: tick === 144 ? "Press north." : "Hold the line."
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
  };
}
