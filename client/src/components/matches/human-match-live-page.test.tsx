import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { loadBritainMapLayout } from "../../lib/britain-map";
import { HumanMatchLivePage } from "./human-match-live-page";
import { SessionProvider } from "../session/session-provider";
import { SESSION_STORAGE_KEY } from "../../lib/session-storage";

class MockWebSocket {
  static instances: MockWebSocket[] = [];

  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  readyState = 0;

  constructor(readonly url: string) {
    MockWebSocket.instances.push(this);
  }

  emitOpen() {
    this.readyState = 1;
    this.onopen?.();
  }

  emitMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent<string>);
  }

  emitError() {
    this.onerror?.();
  }

  emitClose(reason = "") {
    this.readyState = 3;
    this.onclose?.({ reason } as CloseEvent);
  }

  close() {
    this.readyState = 3;
  }
}

function makeEnvelope(tick: number) {
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

function makeJoinableAllianceEnvelope(tick: number) {
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

function makeSoloVisibleEnvelope(tick: number) {
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

function makePublicMatchDetailResponse() {
  return {
    match_id: "match-alpha",
    status: "active",
    map: "britain",
    tick: 142,
    tick_interval_seconds: 30,
    current_player_count: 3,
    max_player_count: 5,
    open_slot_count: 2,
    roster: []
  };
}

function makeJsonResponse(payload: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload
  };
}

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  vi.restoreAllMocks();
  MockWebSocket.instances = [];
});

beforeEach(() => {
  vi.stubGlobal("WebSocket", MockWebSocket);
});

describe("HumanMatchLivePage", () => {
  it("waits for hydration, uses the stored bearer token, and opens the shipped player websocket", async () => {
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "https://hydrated.example/",
        bearerToken: "human-jwt"
      })
    );

    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        match_id: "match-alpha",
        status: "active",
        map: "britain",
        tick: 142,
        tick_interval_seconds: 30,
        current_player_count: 3,
        max_player_count: 5,
        open_slot_count: 2,
        roster: []
      })
    });

    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    expect(fetchSpy).toHaveBeenCalledWith("https://hydrated.example/api/v1/matches/match-alpha", {
      cache: "no-store",
      headers: {
        accept: "application/json"
      }
    });
    expect(MockWebSocket.instances[0]?.url).toBe(
      "wss://hydrated.example/ws/match/match-alpha?viewer=player&token=human-jwt"
    );
  });

  it("renders the player-safe snapshot, identifies the viewed player, and updates on later ticks", async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        match_id: "match-alpha",
        status: "active",
        map: "britain",
        tick: 142,
        tick_interval_seconds: 30,
        current_player_count: 3,
        max_player_count: 5,
        open_slot_count: 2,
        roster: []
      })
    });

    vi.stubGlobal("fetch", fetchSpy);
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitOpen();
    socket?.emitMessage(makeEnvelope(143));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Live player state" })).toBeVisible();
    });

    expect(screen.getByText("player-2")).toBeVisible();
    expect(screen.getByText("War drums.")).toBeVisible();
    expect(screen.getByText("Hold the line.")).toBeVisible();
    expect(screen.getByText("Red Council: Ready.")).toBeVisible();
    expect(screen.getByText("alliance accepted between player-1 and player-2")).toBeVisible();
    expect(screen.getByText("Alliance alliance-red led by player-1")).toBeVisible();
    expect(screen.getByText("Visible enemy army near birmingham")).toBeVisible();
    expect(screen.getByText("Food 263")).toBeVisible();
    const initialMapRegion = screen.getByRole("region", { name: "Britain strategic map" });
    expect(within(initialMapRegion).getByText("Tick 143")).toBeVisible();
    expect(within(initialMapRegion).getByText("Manchester")).toBeVisible();
    expect(within(initialMapRegion).getByText("Owner player-2")).toBeVisible();
    expect(within(initialMapRegion).getByText("Owner hidden")).toBeVisible();
    expect(within(initialMapRegion).getByText("Garrison hidden")).toBeVisible();
    expect(within(initialMapRegion).getByText("player-2 army 5 at Manchester")).toBeVisible();
    expect(within(initialMapRegion).getByText("player-3 army hidden near Birmingham")).toBeVisible();

    socket?.emitMessage(makeEnvelope(144));

    await waitFor(() => {
      expect(screen.getByText("Advance at dawn.")).toBeVisible();
    });

    expect(screen.getByText("Press north.")).toBeVisible();
    expect(screen.getByText("Food 264")).toBeVisible();
    expect(screen.getByText("player-2 at leeds with 5 troops (full)")).toBeVisible();
    const updatedMapRegion = screen.getByRole("region", { name: "Britain strategic map" });
    expect(within(updatedMapRegion).getByText("Tick 144")).toBeVisible();
  });

  it("renders the live messaging composer after the first live player snapshot arrives", async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => makePublicMatchDetailResponse()
    });

    vi.stubGlobal("fetch", fetchSpy);
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    expect(screen.queryByRole("heading", { name: "Live messaging" })).not.toBeInTheDocument();

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitMessage(makeEnvelope(143));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Live messaging" })).toBeVisible();
    });

    expect(screen.getByLabelText("Channel")).toHaveValue("world");
    expect(screen.getByLabelText("Message content")).toHaveValue("");
  });

  it("populates direct and group target choices from the current websocket snapshot", async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => makePublicMatchDetailResponse()
    });

    vi.stubGlobal("fetch", fetchSpy);
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitMessage(makeEnvelope(143));

    fireEvent.change(await screen.findByLabelText("Channel"), { target: { value: "direct" } });

    const directTargetSelect = await screen.findByLabelText("Direct target");
    expect(directTargetSelect).toHaveValue("player-1");
    expect(screen.getAllByRole("option", { name: "player-1" })).toHaveLength(2);
    expect(screen.getAllByRole("option", { name: "player-3" })).toHaveLength(2);
    expect(screen.queryByRole("option", { name: "player-2" })).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Channel"), { target: { value: "group" } });

    const groupTargetSelect = await screen.findByLabelText("Group chat");
    expect(groupTargetSelect).toHaveValue("council-red");
    expect(screen.getByRole("option", { name: "Red Council" })).toBeVisible();
  });

  it("renders text-first group-chat creation controls and derives invite candidates from visible websocket players only", async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => makePublicMatchDetailResponse()
    });

    vi.stubGlobal("fetch", fetchSpy);
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitMessage(makeEnvelope(144));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Create group chat" })).toBeVisible();
    });

    expect(screen.getByLabelText("Group chat name")).toHaveValue("");
    expect(screen.getByRole("checkbox", { name: "player-1" })).not.toBeChecked();
    expect(screen.getByRole("checkbox", { name: "player-3" })).not.toBeChecked();
    expect(screen.queryByRole("checkbox", { name: "player-2" })).not.toBeInTheDocument();
  });

  it("posts group-chat creation to the shipped route with the current websocket tick", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce(makeJsonResponse(makePublicMatchDetailResponse()))
      .mockResolvedValueOnce(
        makeJsonResponse(
          {
            status: "accepted",
            match_id: "match-alpha",
            group_chat: {
              group_chat_id: "council-gold",
              name: "Gold Council",
              member_ids: ["player-2", "player-3"],
              created_by: "player-2",
              created_tick: 144
            }
          },
          202
        )
      );

    vi.stubGlobal("fetch", fetchSpy);
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitMessage(makeEnvelope(143));
    MockWebSocket.instances[0]?.emitMessage(makeEnvelope(144));

    fireEvent.change(await screen.findByLabelText("Group chat name"), {
      target: { value: "Gold Council" }
    });
    fireEvent.click(screen.getByRole("checkbox", { name: "player-3" }));
    fireEvent.click(screen.getByRole("button", { name: "Create group chat" }));

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenNthCalledWith(
        2,
        "http://127.0.0.1:8000/api/v1/matches/match-alpha/group-chats",
        {
          method: "POST",
          cache: "no-store",
          headers: {
            accept: "application/json",
            authorization: "Bearer human-jwt",
            "content-type": "application/json"
          },
          body: JSON.stringify({
            match_id: "match-alpha",
            tick: 144,
            name: "Gold Council",
            member_ids: ["player-3"]
          })
        }
      );
    });
  });

  it("shows accepted group-chat metadata without mutating the visible group-chat list before websocket refresh", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce(makeJsonResponse(makePublicMatchDetailResponse()))
      .mockResolvedValueOnce(
        makeJsonResponse(
          {
            status: "accepted",
            match_id: "match-alpha",
            group_chat: {
              group_chat_id: "council-gold",
              name: "Gold Council",
              member_ids: ["player-2", "player-3"],
              created_by: "player-2",
              created_tick: 144
            }
          },
          202
        )
      );

    vi.stubGlobal("fetch", fetchSpy);
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitMessage(makeEnvelope(144));

    fireEvent.change(await screen.findByLabelText("Group chat name"), {
      target: { value: "Gold Council" }
    });
    fireEvent.click(screen.getByRole("checkbox", { name: "player-3" }));
    fireEvent.click(screen.getByRole("button", { name: "Create group chat" }));

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Group chat accepted: Gold Council.");
    });

    expect(screen.getByRole("status")).toHaveTextContent("Group chat id: council-gold");
    expect(screen.getByRole("status")).toHaveTextContent("Created by: player-2");
    expect(screen.getByRole("status")).toHaveTextContent("Created tick: 144");
    fireEvent.change(screen.getByLabelText("Channel"), { target: { value: "group" } });
    expect(screen.getByLabelText("Group chat")).toHaveValue("council-red");
    expect(screen.queryByRole("option", { name: "Gold Council" })).not.toBeInTheDocument();
  });

  it("preserves the group-chat draft and shows structured creation errors", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce(makeJsonResponse(makePublicMatchDetailResponse()))
      .mockResolvedValueOnce(
        makeJsonResponse(
          {
            error: {
              code: "tick_mismatch",
              message: "Group chat payload tick '143' does not match current match tick '144'."
            }
          },
          400
        )
      );

    vi.stubGlobal("fetch", fetchSpy);
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitMessage(makeEnvelope(144));

    fireEvent.change(await screen.findByLabelText("Group chat name"), {
      target: { value: "Gold Council" }
    });
    fireEvent.click(screen.getByRole("checkbox", { name: "player-1" }));
    fireEvent.click(screen.getByRole("button", { name: "Create group chat" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Group chat payload tick '143' does not match current match tick '144'."
      );
    });

    expect(screen.getByRole("alert")).toHaveTextContent("Error code: tick_mismatch");
    expect(screen.getByRole("alert")).toHaveTextContent("HTTP status: 400");
    expect(screen.getByLabelText("Group chat name")).toHaveValue("Gold Council");
    expect(screen.getByRole("checkbox", { name: "player-1" })).toBeChecked();
  });

  it("shows a deterministic guard when no other visible players can be invited", async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => makePublicMatchDetailResponse()
    });

    vi.stubGlobal("fetch", fetchSpy);
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitMessage(makeSoloVisibleEnvelope(144));

    await waitFor(() => {
      expect(screen.getByText("No other visible players can be invited from the current snapshot.")).toBeVisible();
    });

    expect(screen.getByRole("button", { name: "Create group chat" })).toBeDisabled();
  });

  it("posts world and direct messages to the shipped match-message endpoint with the current live tick", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce(makeJsonResponse(makePublicMatchDetailResponse()))
      .mockResolvedValueOnce(
        makeJsonResponse({
          status: "accepted",
          match_id: "match-alpha",
          message_id: 51,
          channel: "world",
          sender_id: "player-2",
          recipient_id: null,
          tick: 144,
          content: "Stand ready."
        }, 202)
      )
      .mockResolvedValueOnce(
        makeJsonResponse({
          status: "accepted",
          match_id: "match-alpha",
          message_id: 52,
          channel: "direct",
          sender_id: "player-2",
          recipient_id: "player-3",
          tick: 144,
          content: "Hold the western road."
        }, 202)
      );

    vi.stubGlobal("fetch", fetchSpy);
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitMessage(makeEnvelope(143));
    socket?.emitMessage(makeEnvelope(144));

    fireEvent.change(await screen.findByLabelText("Message content"), {
      target: { value: "Stand ready." }
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit message" }));

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenNthCalledWith(2, "http://127.0.0.1:8000/api/v1/matches/match-alpha/messages", {
        method: "POST",
        cache: "no-store",
        headers: {
          accept: "application/json",
          authorization: "Bearer human-jwt",
          "content-type": "application/json"
        },
        body: JSON.stringify({
          match_id: "match-alpha",
          tick: 144,
          channel: "world",
          recipient_id: null,
          content: "Stand ready."
        })
      });
    });

    fireEvent.change(screen.getByLabelText("Channel"), { target: { value: "direct" } });
    fireEvent.change(await screen.findByLabelText("Direct target"), { target: { value: "player-3" } });
    fireEvent.change(screen.getByLabelText("Message content"), {
      target: { value: "Hold the western road." }
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit message" }));

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenNthCalledWith(3, "http://127.0.0.1:8000/api/v1/matches/match-alpha/messages", {
        method: "POST",
        cache: "no-store",
        headers: {
          accept: "application/json",
          authorization: "Bearer human-jwt",
          "content-type": "application/json"
        },
        body: JSON.stringify({
          match_id: "match-alpha",
          tick: 144,
          channel: "direct",
          recipient_id: "player-3",
          content: "Hold the western road."
        })
      });
    });
  });

  it("posts group chat messages to the shipped group-message endpoint with the current live tick", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce(makeJsonResponse(makePublicMatchDetailResponse()))
      .mockResolvedValueOnce(
        makeJsonResponse({
          status: "accepted",
          match_id: "match-alpha",
          group_chat_id: "council-red",
          message: {
            message_id: 81,
            group_chat_id: "council-red",
            sender_id: "player-2",
            tick: 144,
            content: "Reinforce York at dawn."
          }
        }, 202)
      );

    vi.stubGlobal("fetch", fetchSpy);
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitMessage(makeEnvelope(143));
    socket?.emitMessage(makeEnvelope(144));

    fireEvent.change(await screen.findByLabelText("Channel"), { target: { value: "group" } });
    fireEvent.change(await screen.findByLabelText("Group chat"), { target: { value: "council-red" } });
    fireEvent.change(screen.getByLabelText("Message content"), {
      target: { value: "Reinforce York at dawn." }
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit message" }));

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenNthCalledWith(
        2,
        "http://127.0.0.1:8000/api/v1/matches/match-alpha/group-chats/council-red/messages",
        {
          method: "POST",
          cache: "no-store",
          headers: {
            accept: "application/json",
            authorization: "Bearer human-jwt",
            "content-type": "application/json"
          },
          body: JSON.stringify({
            match_id: "match-alpha",
            tick: 144,
            content: "Reinforce York at dawn."
          })
        }
      );
    });
  });

  it("shows deterministic acceptance metadata and clears only the accepted message draft", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce(makeJsonResponse(makePublicMatchDetailResponse()))
      .mockResolvedValueOnce(
        makeJsonResponse({
          status: "accepted",
          match_id: "match-alpha",
          message_id: 51,
          channel: "world",
          sender_id: "player-2",
          recipient_id: null,
          tick: 144,
          content: "Stand ready."
        }, 202)
      );

    vi.stubGlobal("fetch", fetchSpy);
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitMessage(makeEnvelope(144));

    fireEvent.change(await screen.findByLabelText("Message content"), {
      target: { value: "Stand ready." }
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit message" }));

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent(
        "Accepted world message 51 for tick 144 from player-2."
      );
    });

    expect(screen.getByLabelText("Message content")).toHaveValue("");
    expect(screen.queryByText("Stand ready.")).not.toBeInTheDocument();
  });

  it("preserves the current draft and shows structured message errors", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce(makeJsonResponse(makePublicMatchDetailResponse()))
      .mockResolvedValueOnce(
        makeJsonResponse(
          {
            error: {
              code: "tick_mismatch",
              message: "Message payload tick '143' does not match current match tick '144'."
            }
          },
          400
        )
      );

    vi.stubGlobal("fetch", fetchSpy);
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitMessage(makeEnvelope(144));

    fireEvent.change(await screen.findByLabelText("Message content"), {
      target: { value: "Stand ready." }
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit message" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Message payload tick '143' does not match current match tick '144'."
      );
    });

    expect(screen.getByRole("alert")).toHaveTextContent("Error code: tick_mismatch");
    expect(screen.getByRole("alert")).toHaveTextContent("HTTP status: 400");
    expect(screen.getByLabelText("Message content")).toHaveValue("Stand ready.");
  });

  it("renders live diplomacy controls and derives treaty counterparties from the websocket snapshot", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(makeJsonResponse(makePublicMatchDetailResponse()));

    vi.stubGlobal("fetch", fetchSpy);
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitMessage(makeEnvelope(144));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Live diplomacy" })).toBeVisible();
    });

    const treatyCounterparty = screen.getByLabelText("Treaty counterparty");
    expect(screen.getByLabelText("Treaty action")).toHaveValue("propose");
    expect(screen.getByLabelText("Treaty type")).toHaveValue("non_aggression");
    expect(treatyCounterparty).toHaveValue("player-1");
    expect(screen.getByRole("option", { name: "player-1" })).toBeVisible();
    expect(screen.getByRole("option", { name: "player-3" })).toBeVisible();
    expect(screen.queryByRole("option", { name: "player-2" })).not.toBeInTheDocument();
  });

  it("posts treaty actions to the shipped route with the current websocket state and shows accepted metadata only", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce(makeJsonResponse(makePublicMatchDetailResponse()))
      .mockResolvedValueOnce(
        makeJsonResponse(
          {
            status: "accepted",
            match_id: "match-alpha",
            treaty: {
              treaty_id: 8,
              player_a_id: "player-2",
              player_b_id: "player-3",
              treaty_type: "trade",
              status: "proposed",
              proposed_by: "player-2",
              proposed_tick: 144,
              signed_tick: null,
              withdrawn_by: null,
              withdrawn_tick: null
            }
          },
          202
        )
      );

    vi.stubGlobal("fetch", fetchSpy);
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitMessage(makeEnvelope(144));

    fireEvent.change(await screen.findByLabelText("Treaty action"), { target: { value: "propose" } });
    fireEvent.change(screen.getByLabelText("Treaty type"), { target: { value: "trade" } });
    fireEvent.change(screen.getByLabelText("Treaty counterparty"), { target: { value: "player-3" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit treaty" }));

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenNthCalledWith(2, "http://127.0.0.1:8000/api/v1/matches/match-alpha/treaties", {
        method: "POST",
        cache: "no-store",
        headers: {
          accept: "application/json",
          authorization: "Bearer human-jwt",
          "content-type": "application/json"
        },
        body: JSON.stringify({
          match_id: "match-alpha",
          counterparty_id: "player-3",
          action: "propose",
          treaty_type: "trade"
        })
      });
    });

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Treaty accepted: trade with player-3.");
    });

    expect(screen.getByRole("status")).toHaveTextContent("Treaty id: 8");
    expect(screen.getByRole("status")).toHaveTextContent("Counterparties: player-2 and player-3");
    expect(screen.getByRole("status")).toHaveTextContent("Type: trade");
    expect(screen.getByRole("status")).toHaveTextContent("Status: proposed");
    expect(screen.getByRole("status")).toHaveTextContent("Proposed by: player-2");
    expect(screen.getByRole("status")).toHaveTextContent("Proposed tick: 144");
    expect(screen.getByRole("status")).toHaveTextContent("Signed tick: not signed");
    expect(screen.getByText("Alliance alliance-red led by player-1")).toBeVisible();
  });

  it("reports treaty acceptance against the other player when the current player accepts", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce(makeJsonResponse(makePublicMatchDetailResponse()))
      .mockResolvedValueOnce(
        makeJsonResponse(
          {
            status: "accepted",
            match_id: "match-alpha",
            treaty: {
              treaty_id: 8,
              player_a_id: "player-2",
              player_b_id: "player-3",
              treaty_type: "trade",
              status: "accepted",
              proposed_by: "player-3",
              proposed_tick: 143,
              signed_tick: 144,
              withdrawn_by: null,
              withdrawn_tick: null
            }
          },
          202
        )
      );

    vi.stubGlobal("fetch", fetchSpy);
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitMessage(makeEnvelope(144));

    fireEvent.change(await screen.findByLabelText("Treaty action"), { target: { value: "accept" } });
    fireEvent.change(screen.getByLabelText("Treaty type"), { target: { value: "trade" } });
    fireEvent.change(screen.getByLabelText("Treaty counterparty"), { target: { value: "player-3" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit treaty" }));

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Treaty accepted: trade with player-3.");
    });

    expect(screen.getByRole("status")).toHaveTextContent("Status: accepted");
    expect(screen.getByRole("status")).toHaveTextContent("Proposed by: player-3");
    expect(screen.getByRole("status")).toHaveTextContent("Proposed tick: 143");
    expect(screen.getByRole("status")).toHaveTextContent("Signed tick: 144");
  });

  it("preserves treaty draft state and surfaces structured treaty errors", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce(makeJsonResponse(makePublicMatchDetailResponse()))
      .mockResolvedValueOnce(
        makeJsonResponse(
          {
            error: {
              code: "tick_mismatch",
              message: "Treaty action no longer matches the current diplomacy tick."
            }
          },
          409
        )
      );

    vi.stubGlobal("fetch", fetchSpy);
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitMessage(makeEnvelope(144));

    fireEvent.change(await screen.findByLabelText("Treaty action"), { target: { value: "withdraw" } });
    fireEvent.change(screen.getByLabelText("Treaty type"), { target: { value: "defensive" } });
    fireEvent.change(screen.getByLabelText("Treaty counterparty"), { target: { value: "player-3" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit treaty" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Treaty action no longer matches the current diplomacy tick."
      );
    });

    expect(screen.getByRole("alert")).toHaveTextContent("Error code: tick_mismatch");
    expect(screen.getByRole("alert")).toHaveTextContent("HTTP status: 409");
    expect(screen.getByLabelText("Treaty action")).toHaveValue("withdraw");
    expect(screen.getByLabelText("Treaty type")).toHaveValue("defensive");
    expect(screen.getByLabelText("Treaty counterparty")).toHaveValue("player-3");
  });

  it("filters alliance join choices to visible alliances the current player is not already in", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(makeJsonResponse(makePublicMatchDetailResponse()));

    vi.stubGlobal("fetch", fetchSpy);
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitMessage(makeEnvelope(144));

    fireEvent.change(await screen.findByLabelText("Alliance action"), { target: { value: "join" } });

    expect(screen.getByLabelText("Alliance action")).toHaveValue("join");
    expect(screen.getByLabelText("Join alliance")).toHaveValue("");
    expect(screen.getByRole("option", { name: "No joinable alliances" })).toBeVisible();
    expect(screen.queryByRole("option", { name: "alliance-red" })).not.toBeInTheDocument();
  });

  it("posts alliance create, join, and leave actions using the shipped route shapes", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce(makeJsonResponse(makePublicMatchDetailResponse()))
      .mockResolvedValueOnce(
        makeJsonResponse(
          {
            status: "accepted",
            match_id: "match-alpha",
            player_id: "player-2",
            alliance: {
              alliance_id: "alliance-blue",
              name: "Blue League",
              leader_id: "player-2",
              formed_tick: 144,
              members: [{ player_id: "player-2", joined_tick: 144 }]
            }
          },
          202
        )
      )
      .mockResolvedValueOnce(
        makeJsonResponse(
          {
            status: "accepted",
            match_id: "match-alpha",
            player_id: "player-2",
            alliance: {
              alliance_id: "alliance-red",
              name: "alliance-red",
              leader_id: "player-1",
              formed_tick: 140,
              members: [
                { player_id: "player-1", joined_tick: 140 },
                { player_id: "player-2", joined_tick: 144 }
              ]
            }
          },
          202
        )
      )
      .mockResolvedValueOnce(
        makeJsonResponse(
          {
            status: "accepted",
            match_id: "match-alpha",
            player_id: "player-2",
            alliance: {
              alliance_id: "alliance-red",
              name: "alliance-red",
              leader_id: "player-1",
              formed_tick: 140,
              members: [{ player_id: "player-1", joined_tick: 140 }]
            }
          },
          202
        )
      );

    vi.stubGlobal("fetch", fetchSpy);
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitMessage(makeJoinableAllianceEnvelope(144));

    fireEvent.change(await screen.findByLabelText("Alliance action"), { target: { value: "create" } });
    fireEvent.change(screen.getByLabelText("Alliance name"), { target: { value: "Blue League" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit alliance" }));

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenNthCalledWith(2, "http://127.0.0.1:8000/api/v1/matches/match-alpha/alliances", {
        method: "POST",
        cache: "no-store",
        headers: {
          accept: "application/json",
          authorization: "Bearer human-jwt",
          "content-type": "application/json"
        },
        body: JSON.stringify({
          match_id: "match-alpha",
          action: "create",
          name: "Blue League"
        })
      });
    });

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Alliance accepted: created Blue League.");
    });

    expect(screen.getByRole("status")).toHaveTextContent("Action: create");
    expect(screen.getByRole("status")).toHaveTextContent("Player id: player-2");
    expect(screen.getByRole("status")).toHaveTextContent("Alliance id: alliance-blue");
    expect(screen.getByRole("status")).toHaveTextContent("Alliance name: Blue League");
    expect(screen.getByRole("status")).toHaveTextContent("Leader id: player-2");
    expect(screen.getByRole("status")).toHaveTextContent("Formed tick: 144");
    expect(screen.getByRole("status")).toHaveTextContent("Accepted player joined tick: 144");

    fireEvent.change(screen.getByLabelText("Alliance action"), { target: { value: "join" } });
    fireEvent.change(await screen.findByLabelText("Join alliance"), { target: { value: "alliance-red" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit alliance" }));

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenNthCalledWith(3, "http://127.0.0.1:8000/api/v1/matches/match-alpha/alliances", {
        method: "POST",
        cache: "no-store",
        headers: {
          accept: "application/json",
          authorization: "Bearer human-jwt",
          "content-type": "application/json"
        },
        body: JSON.stringify({
          match_id: "match-alpha",
          action: "join",
          alliance_id: "alliance-red"
        })
      });
    });

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Alliance accepted: joined alliance-red.");
    });

    expect(screen.getByRole("status")).toHaveTextContent("Action: join");
    expect(screen.getByRole("status")).toHaveTextContent("Alliance id: alliance-red");
    expect(screen.getByRole("status")).toHaveTextContent("Leader id: player-1");
    expect(screen.getByRole("status")).toHaveTextContent("Formed tick: 140");
    expect(screen.getByRole("status")).toHaveTextContent("Accepted player joined tick: 144");

    fireEvent.change(screen.getByLabelText("Alliance action"), { target: { value: "leave" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit alliance" }));

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenNthCalledWith(4, "http://127.0.0.1:8000/api/v1/matches/match-alpha/alliances", {
        method: "POST",
        cache: "no-store",
        headers: {
          accept: "application/json",
          authorization: "Bearer human-jwt",
          "content-type": "application/json"
        },
        body: JSON.stringify({
          match_id: "match-alpha",
          action: "leave"
        })
      });
    });

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Alliance accepted: left alliance-red.");
    });

    expect(screen.getByRole("status")).toHaveTextContent("Action: leave");
    expect(screen.getByRole("status")).toHaveTextContent(
      "Accepted player membership: player-2 not present in accepted alliance record"
    );
  });

  it("shows accepted alliance metadata while the websocket snapshot remains authoritative for visible alliance state", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce(makeJsonResponse(makePublicMatchDetailResponse()))
      .mockResolvedValueOnce(
        makeJsonResponse(
          {
            status: "accepted",
            match_id: "match-alpha",
            player_id: "player-2",
            alliance: {
              alliance_id: "alliance-red",
              name: "alliance-red",
              leader_id: "player-1",
              formed_tick: 140,
              members: [
                { player_id: "player-1", joined_tick: 140 },
                { player_id: "player-2", joined_tick: 144 }
              ]
            }
          },
          202
        )
      );

    vi.stubGlobal("fetch", fetchSpy);
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitMessage(makeJoinableAllianceEnvelope(144));

    await waitFor(() => {
      expect(screen.getByText("Current alliance: none")).toBeVisible();
    });

    expect(screen.getByText("Alliance alliance-red led by player-1")).toBeVisible();

    fireEvent.change(await screen.findByLabelText("Alliance action"), { target: { value: "join" } });
    fireEvent.change(screen.getByLabelText("Join alliance"), { target: { value: "alliance-red" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit alliance" }));

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Alliance accepted: joined alliance-red.");
    });

    expect(screen.getByRole("status")).toHaveTextContent("Player id: player-2");
    expect(screen.getByRole("status")).toHaveTextContent("Alliance id: alliance-red");
    expect(screen.getByRole("status")).toHaveTextContent("Accepted player joined tick: 144");
    expect(screen.getByText("Current alliance: none")).toBeVisible();
    expect(screen.getByText("Alliance alliance-red led by player-1")).toBeVisible();

    socket?.emitMessage(makeEnvelope(145));

    await waitFor(() => {
      expect(screen.getByText("Current alliance: alliance-red")).toBeVisible();
    });
  });

  it("preserves alliance draft state and surfaces structured alliance errors", async () => {
    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce(makeJsonResponse(makePublicMatchDetailResponse()))
      .mockResolvedValueOnce(
        makeJsonResponse(
          {
            error: {
              code: "alliance_membership_conflict",
              message: "Player-2 is already a member of alliance-red."
            }
          },
          409
        )
      );

    vi.stubGlobal("fetch", fetchSpy);
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitMessage(makeEnvelope(144));

    fireEvent.change(await screen.findByLabelText("Alliance action"), { target: { value: "create" } });
    fireEvent.change(screen.getByLabelText("Alliance name"), { target: { value: "Blue League" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit alliance" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Player-2 is already a member of alliance-red.");
    });

    expect(screen.getByRole("alert")).toHaveTextContent("Error code: alliance_membership_conflict");
    expect(screen.getByRole("alert")).toHaveTextContent("HTTP status: 409");
    expect(screen.getByLabelText("Alliance action")).toHaveValue("create");
    expect(screen.getByLabelText("Alliance name")).toHaveValue("Blue League");
  });

  it("shows a deterministic guard when no stored bearer token exists and preserves the page without opening the socket", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Live updates unavailable");
    });

    expect(
      screen.getByText("This live player page requires a stored human bearer token before it can connect.")
    ).toBeVisible();
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(MockWebSocket.instances).toHaveLength(0);
  });

  it("shows an inactive state for non-active matches and skips the websocket connection", async () => {
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        match_id: "match-alpha",
        status: "paused",
        map: "britain",
        tick: 142,
        tick_interval_seconds: 30,
        current_player_count: 3,
        max_player_count: 5,
        open_slot_count: 2,
        roster: []
      })
    });

    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Live updates unavailable");
    });

    expect(screen.getByText("This match is paused, so the authenticated live page is not active.")).toBeVisible();
    expect(MockWebSocket.instances).toHaveLength(0);
    const mapRegion = screen.getByRole("region", { name: "Britain strategic map" });
    expect(within(mapRegion).getByText("Player feed offline")).toBeVisible();
    expect(within(mapRegion).getByText("No live strategic map data is available yet.")).toBeVisible();
  });

  it("preserves the last confirmed snapshot after socket failure", async () => {
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        match_id: "match-alpha",
        status: "active",
        map: "britain",
        tick: 142,
        tick_interval_seconds: 30,
        current_player_count: 3,
        max_player_count: 5,
        open_slot_count: 2,
        roster: []
      })
    });

    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitOpen();
    socket?.emitMessage(makeEnvelope(143));

    await waitFor(() => {
      expect(screen.getByText("War drums.")).toBeVisible();
    });

    socket?.emitError();

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Live connection lost");
    });

    expect(screen.getByText("Showing the last confirmed player snapshot. Reconnect to resume live updates.")).toBeVisible();
    expect(screen.getByText("War drums.")).toBeVisible();
    expect(screen.getAllByText("Not live").length).toBeGreaterThan(0);
    const mapRegion = screen.getByRole("region", { name: "Britain strategic map" });
    expect(within(mapRegion).getByText("Player feed offline")).toBeVisible();
    expect(within(mapRegion).getByText("Manchester")).toBeVisible();
  });

  it("fails closed on invalid player websocket payloads while preserving the last confirmed snapshot", async () => {
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        match_id: "match-alpha",
        status: "active",
        map: "britain",
        tick: 142,
        tick_interval_seconds: 30,
        current_player_count: 3,
        max_player_count: 5,
        open_slot_count: 2,
        roster: []
      })
    });

    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitOpen();
    socket?.emitMessage(makeEnvelope(143));

    await waitFor(() => {
      expect(screen.getByText("War drums.")).toBeVisible();
    });

    socket?.emitMessage({
      type: "tick_update",
      data: {
        match_id: "match-alpha",
        viewer_role: "player",
        player_id: "player-2",
        state: {
          tick: "broken"
        }
      }
    });

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Live connection lost");
    });

    expect(screen.getByText("War drums.")).toBeVisible();
  });

  it("surfaces the backend websocket auth error envelope instead of the generic unavailable text", async () => {
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        match_id: "match-alpha",
        status: "active",
        map: "britain",
        tick: 142,
        tick_interval_seconds: 30,
        current_player_count: 3,
        max_player_count: 5,
        open_slot_count: 2,
        roster: []
      })
    });

    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];

    socket?.emitMessage({
      error: {
        code: "player_auth_mismatch",
        message: "This bearer token does not belong to the requested player."
      }
    });

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Live updates unavailable");
    });

    expect(
      screen.getByText("This bearer token does not belong to the requested player.")
    ).toBeVisible();
    expect(screen.queryByText("Live updates are unavailable right now.")).not.toBeInTheDocument();
  });

  it("surfaces the not-joined close reason while preserving the last confirmed snapshot", async () => {
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        match_id: "match-alpha",
        status: "active",
        map: "britain",
        tick: 142,
        tick_interval_seconds: 30,
        current_player_count: 3,
        max_player_count: 5,
        open_slot_count: 2,
        roster: []
      })
    });

    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitOpen();
    socket?.emitMessage(makeEnvelope(143));

    await waitFor(() => {
      expect(screen.getByText("War drums.")).toBeVisible();
    });

    socket?.emitClose("human_not_joined");

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent("Live connection lost");
    });

    expect(
      screen.getByText("Join this match as a human player before opening the authenticated live page.")
    ).toBeVisible();
    expect(screen.getByText("War drums.")).toBeVisible();
    expect(screen.queryByText("Showing the last confirmed player snapshot. Reconnect to resume live updates.")).not.toBeInTheDocument();
  });

  it("renders boring order drafts after the first live snapshot and allows adding and removing each order type", async () => {
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          match_id: "match-alpha",
          status: "active",
          map: "britain",
          tick: 142,
          tick_interval_seconds: 30,
          current_player_count: 3,
          max_player_count: 5,
          open_slot_count: 2,
          roster: []
        })
      })
    );

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    expect(screen.queryByRole("heading", { name: "Order Drafts" })).not.toBeInTheDocument();

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitOpen();
    socket?.emitMessage(makeEnvelope(143));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Order Drafts" })).toBeVisible();
    });

    fireEvent.click(screen.getByRole("button", { name: "Add movement order" }));
    fireEvent.click(screen.getByRole("button", { name: "Add recruitment order" }));
    fireEvent.click(screen.getByRole("button", { name: "Add upgrade order" }));
    fireEvent.click(screen.getByRole("button", { name: "Add transfer order" }));

    expect(screen.getByLabelText("Movement army ID 1")).toBeVisible();
    expect(screen.getByLabelText("Recruitment city 1")).toBeVisible();
    expect(screen.getByLabelText("Upgrade city 1")).toBeVisible();
    expect(screen.getByLabelText("Transfer destination 1")).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "Remove movement order 1" }));
    fireEvent.click(screen.getByRole("button", { name: "Remove recruitment order 1" }));
    fireEvent.click(screen.getByRole("button", { name: "Remove upgrade order 1" }));
    fireEvent.click(screen.getByRole("button", { name: "Remove transfer order 1" }));

    expect(screen.queryByLabelText("Movement army ID 1")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Recruitment city 1")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Upgrade city 1")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Transfer destination 1")).not.toBeInTheDocument();
  });

  it("submits current draft orders for the current websocket tick, shows accepted confirmation, and clears the draft", async () => {
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "https://hydrated.example/",
        bearerToken: "human-jwt"
      })
    );

    const fetchSpy = vi.fn().mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

      if (url === "https://hydrated.example/api/v1/matches/match-alpha") {
        return {
          ok: true,
          json: async () => makePublicMatchDetailResponse()
        };
      }

      if (url === "https://hydrated.example/api/v1/matches/match-alpha/commands") {
        return {
          ok: true,
          status: 202,
          json: async () => ({
            status: "accepted",
            match_id: "match-alpha",
            player_id: "player-2",
            tick: 144,
            orders: {
              status: "accepted",
              match_id: "match-alpha",
              player_id: "player-2",
              tick: 144,
              submission_index: 3
            },
            messages: [],
            treaties: [],
            alliance: null
          })
        };
      }

      throw new Error(`Unexpected fetch call: ${url} ${init?.method ?? "GET"}`);
    });

    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitOpen();
    socket?.emitMessage(makeEnvelope(144));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Order Drafts" })).toBeVisible();
    });

    fireEvent.click(screen.getByRole("button", { name: "Add movement order" }));
    fireEvent.change(screen.getByLabelText("Movement army ID 1"), {
      target: { value: "army-1" }
    });
    fireEvent.change(screen.getByLabelText("Movement destination 1"), {
      target: { value: "leeds" }
    });

    fireEvent.click(screen.getByRole("button", { name: "Submit drafted orders" }));

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledTimes(2);
    });

    expect(fetchSpy).toHaveBeenNthCalledWith(2, "https://hydrated.example/api/v1/matches/match-alpha/commands", {
      method: "POST",
      cache: "no-store",
      headers: {
        accept: "application/json",
        authorization: "Bearer human-jwt",
        "content-type": "application/json"
      },
      body: JSON.stringify({
        match_id: "match-alpha",
        tick: 144,
        orders: {
          movements: [{ army_id: "army-1", destination: "leeds" }],
          recruitment: [],
          upgrades: [],
          transfers: []
        },
        messages: [],
        treaties: [],
        alliance: null
      })
    });
    expect(screen.getByText("Orders accepted for tick 144 from player-2.")).toBeVisible();
    expect(screen.queryByLabelText("Movement army ID 1")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Movement destination 1")).not.toBeInTheDocument();
  });

  it("blocks incomplete draft rows before submission and preserves the draft for correction", async () => {
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => makePublicMatchDetailResponse()
    });

    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitOpen();
    socket?.emitMessage(makeEnvelope(143));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Order Drafts" })).toBeVisible();
    });

    fireEvent.click(screen.getByRole("button", { name: "Add recruitment order" }));
    fireEvent.change(screen.getByLabelText("Recruitment city 1"), {
      target: { value: "manchester" }
    });

    fireEvent.click(screen.getByRole("button", { name: "Submit drafted orders" }));

    await waitFor(() => {
      expect(screen.getByText("Recruitment order 1 requires city and troops greater than zero.")).toBeVisible();
    });

    expect(screen.getByText("Error code: invalid_order_draft")).toBeVisible();
    expect(screen.getByText("HTTP status: 400")).toBeVisible();
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText("Recruitment city 1")).toHaveValue("manchester");
    expect(screen.getByLabelText("Recruitment troops 1")).toHaveValue(null);
  });

  it("preserves draft rows and shows structured command failure details when submission is rejected", async () => {
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    const fetchSpy = vi.fn().mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

      if (url === "http://127.0.0.1:8000/api/v1/matches/match-alpha") {
        return {
          ok: true,
          json: async () => makePublicMatchDetailResponse()
        };
      }

      if (url === "http://127.0.0.1:8000/api/v1/matches/match-alpha/commands") {
        return {
          ok: false,
          status: 409,
          json: async () => ({
            error: {
              code: "tick_mismatch",
              message: "Orders already closed for tick 143."
            }
          })
        };
      }

      throw new Error(`Unexpected fetch call: ${url} ${init?.method ?? "GET"}`);
    });

    vi.stubGlobal("fetch", fetchSpy);

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const socket = MockWebSocket.instances[0];
    socket?.emitOpen();
    socket?.emitMessage(makeEnvelope(143));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Order Drafts" })).toBeVisible();
    });

    fireEvent.click(screen.getByRole("button", { name: "Add transfer order" }));
    fireEvent.change(screen.getByLabelText("Transfer destination 1"), {
      target: { value: "alliance-red" }
    });
    fireEvent.change(screen.getByLabelText("Transfer resource 1"), {
      target: { value: "money" }
    });
    fireEvent.change(screen.getByLabelText("Transfer amount 1"), {
      target: { value: "25" }
    });

    fireEvent.click(screen.getByRole("button", { name: "Submit drafted orders" }));

    await waitFor(() => {
      expect(screen.getByText("Orders already closed for tick 143.")).toBeVisible();
    });

    expect(fetchSpy).toHaveBeenNthCalledWith(2, "http://127.0.0.1:8000/api/v1/matches/match-alpha/commands", {
      method: "POST",
      cache: "no-store",
      headers: {
        accept: "application/json",
        authorization: "Bearer human-jwt",
        "content-type": "application/json"
      },
      body: JSON.stringify({
        match_id: "match-alpha",
        tick: 143,
        orders: {
          movements: [],
          recruitment: [],
          upgrades: [],
          transfers: [{ to: "alliance-red", resource: "money", amount: 25 }]
        },
        messages: [],
        treaties: [],
        alliance: null
      })
    });
    expect(screen.getByText("Error code: tick_mismatch")).toBeVisible();
    expect(screen.getByText("HTTP status: 409")).toBeVisible();
    expect(screen.getByLabelText("Transfer destination 1")).toHaveValue("alliance-red");
    expect(screen.getByLabelText("Transfer resource 1")).toHaveValue("money");
    expect(screen.getByLabelText("Transfer amount 1")).toHaveValue(25);
  });

  it("clicking visible map markers highlights the selection, shows a safe inspector, and prefills blank draft fields with explicit helper actions", async () => {
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => makePublicMatchDetailResponse()
      })
    );

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitOpen();
    MockWebSocket.instances[0]?.emitMessage(makeEnvelope(144));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Order Drafts" })).toBeVisible();
    });

    fireEvent.click(screen.getByRole("button", { name: "Add movement order" }));

    const manchesterCityButton = screen.getByRole("button", { name: "Select city Manchester" });
    fireEvent.click(manchesterCityButton);

    expect(manchesterCityButton).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("heading", { name: "Map selection inspector" })).toBeVisible();
    const inspectorRegion = screen.getByRole("region", { name: "Map selection inspector" });
    expect(within(inspectorRegion).getByText("Selected city: Manchester")).toBeVisible();
    expect(within(inspectorRegion).getByText("Owner player-2")).toBeVisible();
    expect(within(inspectorRegion).getByText("Visible garrison 7")).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "Use selected marker for movement destination 1" }));
    expect(screen.getByLabelText("Movement destination 1")).toHaveValue("manchester");

    const armyButton = screen.getByRole("button", { name: "Select army army-1 at Leeds" });
    fireEvent.click(armyButton);

    expect(armyButton).toHaveAttribute("aria-pressed", "true");
    expect(within(inspectorRegion).getByText("Selected army: army-1")).toBeVisible();
    expect(within(inspectorRegion).getByText("Owner player-2")).toBeVisible();
    expect(within(inspectorRegion).getByText("Visible troops 5")).toBeVisible();
    expect(within(inspectorRegion).getByText("Visible location Leeds")).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "Use selected army for movement army ID 1" }));
    expect(screen.getByLabelText("Movement army ID 1")).toHaveValue("army-1");

    fireEvent.click(screen.getByRole("button", { name: "Add recruitment order" }));
    fireEvent.click(manchesterCityButton);
    fireEvent.click(screen.getByRole("button", { name: "Use selected city for recruitment city 1" }));
    expect(screen.getByLabelText("Recruitment city 1")).toHaveValue("manchester");
  });

  it("preserves existing draft values and shows deterministic guidance when a selected marker is invalid for the requested helper", async () => {
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        apiBaseUrl: "http://127.0.0.1:8000",
        bearerToken: "human-jwt"
      })
    );

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => makePublicMatchDetailResponse()
      })
    );

    render(
      <SessionProvider>
        <HumanMatchLivePage matchId="match-alpha" mapLayout={loadBritainMapLayout()} />
      </SessionProvider>
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitOpen();
    MockWebSocket.instances[0]?.emitMessage(makeEnvelope(143));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Order Drafts" })).toBeVisible();
    });

    fireEvent.click(screen.getByRole("button", { name: "Add recruitment order" }));
    fireEvent.change(screen.getByLabelText("Recruitment city 1"), {
      target: { value: "existing-city" }
    });

    const partialArmyButton = screen.getByRole("button", { name: "Select army army-2 near Birmingham" });
    fireEvent.click(partialArmyButton);

    const inspectorRegion = screen.getByRole("region", { name: "Map selection inspector" });
    expect(within(inspectorRegion).getByText("Selected army: army-2")).toBeVisible();
    expect(within(inspectorRegion).getByText("Visible location hidden or unknown")).toBeVisible();
    expect(within(inspectorRegion).getByText("Visible troops hidden or unknown")).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "Use selected city for recruitment city 1" }));

    expect(screen.getByLabelText("Recruitment city 1")).toHaveValue("existing-city");
    expect(screen.getByRole("status")).toHaveTextContent(
      "Selection helper could not update recruitment city 1: the selected army does not expose a visible city."
    );

    fireEvent.click(screen.getByRole("button", { name: "Add transfer order" }));
    fireEvent.change(screen.getByLabelText("Transfer destination 1"), {
      target: { value: "player-3" }
    });

    const hiddenCityButton = screen.getByRole("button", { name: "Select city Birmingham" });
    fireEvent.click(hiddenCityButton);
    expect(within(inspectorRegion).getByText("Selected city: Birmingham")).toBeVisible();
    expect(within(inspectorRegion).getByText("Owner hidden or unknown")).toBeVisible();
    expect(within(inspectorRegion).getByText("Garrison hidden or unknown")).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "Use selected marker for transfer destination 1" }));

    expect(screen.getByLabelText("Transfer destination 1")).toHaveValue("player-3");
    expect(screen.getByRole("status")).toHaveTextContent(
      "Selection helper could not update transfer destination 1: visible city selections cannot fill transfer destinations."
    );
  });
});
