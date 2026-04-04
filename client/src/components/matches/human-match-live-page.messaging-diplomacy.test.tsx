import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  expectFetchCall,
  makeEnvelope,
  makeFetchSpyWithGuidedSession,
  makeJoinableAllianceEnvelope,
  makeJsonResponse,
  makePublicMatchDetailResponse,
  makeSoloVisibleEnvelope,
  MockWebSocket,
  renderHumanMatchLivePage,
  setStoredSession
} from "./human-match-live-page-test-helpers";

describe("HumanMatchLivePage messaging and diplomacy", () => {
  it("renders the live messaging composer after the first live player snapshot arrives", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => makePublicMatchDetailResponse()
      })
    );
    setStoredSession();
    renderHumanMatchLivePage();

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
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => makePublicMatchDetailResponse()
      })
    );
    setStoredSession();
    renderHumanMatchLivePage();

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
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => makePublicMatchDetailResponse()
      })
    );
    setStoredSession();
    renderHumanMatchLivePage();

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
    const fetchSpy = makeFetchSpyWithGuidedSession(
      makeJsonResponse(makePublicMatchDetailResponse()),
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
    setStoredSession();
    renderHumanMatchLivePage();

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
      expectFetchCall(
        fetchSpy,
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
    const fetchSpy = makeFetchSpyWithGuidedSession(
      makeJsonResponse(makePublicMatchDetailResponse()),
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
    setStoredSession();
    renderHumanMatchLivePage();

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitMessage(makeEnvelope(144));

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
    const fetchSpy = makeFetchSpyWithGuidedSession(
      makeJsonResponse(makePublicMatchDetailResponse()),
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
    setStoredSession();
    renderHumanMatchLivePage();

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
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => makePublicMatchDetailResponse()
      })
    );
    setStoredSession();
    renderHumanMatchLivePage();

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
    const fetchSpy = makeFetchSpyWithGuidedSession(
      makeJsonResponse(makePublicMatchDetailResponse()),
      makeJsonResponse({
        status: "accepted",
        match_id: "match-alpha",
        message_id: 51,
        channel: "world",
        sender_id: "player-2",
        recipient_id: null,
        tick: 144,
        content: "Stand ready."
      }, 202),
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
    setStoredSession();
    renderHumanMatchLivePage();

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitMessage(makeEnvelope(143));
    MockWebSocket.instances[0]?.emitMessage(makeEnvelope(144));

    fireEvent.change(await screen.findByLabelText("Message content"), {
      target: { value: "Stand ready." }
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit message" }));

    await waitFor(() => {
      expectFetchCall(fetchSpy, "http://127.0.0.1:8000/api/v1/matches/match-alpha/messages", {
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
      }, 1);
    });

    fireEvent.change(screen.getByLabelText("Channel"), { target: { value: "direct" } });
    fireEvent.change(await screen.findByLabelText("Direct target"), { target: { value: "player-3" } });
    fireEvent.change(screen.getByLabelText("Message content"), {
      target: { value: "Hold the western road." }
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit message" }));

    await waitFor(() => {
      expectFetchCall(fetchSpy, "http://127.0.0.1:8000/api/v1/matches/match-alpha/messages", {
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
      }, 2);
    });
  });

  it("posts group chat messages to the shipped group-message endpoint with the current live tick", async () => {
    const fetchSpy = makeFetchSpyWithGuidedSession(
      makeJsonResponse(makePublicMatchDetailResponse()),
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
    setStoredSession();
    renderHumanMatchLivePage();

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitMessage(makeEnvelope(143));
    MockWebSocket.instances[0]?.emitMessage(makeEnvelope(144));

    fireEvent.change(await screen.findByLabelText("Channel"), { target: { value: "group" } });
    fireEvent.change(await screen.findByLabelText("Group chat"), { target: { value: "council-red" } });
    fireEvent.change(screen.getByLabelText("Message content"), {
      target: { value: "Reinforce York at dawn." }
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit message" }));

    await waitFor(() => {
      expectFetchCall(
        fetchSpy,
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
    const fetchSpy = makeFetchSpyWithGuidedSession(
      makeJsonResponse(makePublicMatchDetailResponse()),
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
    setStoredSession();
    renderHumanMatchLivePage();

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
    const fetchSpy = makeFetchSpyWithGuidedSession(
      makeJsonResponse(makePublicMatchDetailResponse()),
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
    setStoredSession();
    renderHumanMatchLivePage();

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
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(makeJsonResponse(makePublicMatchDetailResponse()))
    );
    setStoredSession();
    renderHumanMatchLivePage();

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
    const fetchSpy = makeFetchSpyWithGuidedSession(
      makeJsonResponse(makePublicMatchDetailResponse()),
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
    setStoredSession();
    renderHumanMatchLivePage();

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitMessage(makeEnvelope(144));

    fireEvent.change(await screen.findByLabelText("Treaty action"), { target: { value: "propose" } });
    fireEvent.change(screen.getByLabelText("Treaty type"), { target: { value: "trade" } });
    fireEvent.change(screen.getByLabelText("Treaty counterparty"), { target: { value: "player-3" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit treaty" }));

    await waitFor(() => {
      expectFetchCall(fetchSpy, "http://127.0.0.1:8000/api/v1/matches/match-alpha/treaties", {
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
    const fetchSpy = makeFetchSpyWithGuidedSession(
      makeJsonResponse(makePublicMatchDetailResponse()),
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
    setStoredSession();
    renderHumanMatchLivePage();

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
    const fetchSpy = makeFetchSpyWithGuidedSession(
      makeJsonResponse(makePublicMatchDetailResponse()),
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
    setStoredSession();
    renderHumanMatchLivePage();

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
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(makeJsonResponse(makePublicMatchDetailResponse()))
    );
    setStoredSession();
    renderHumanMatchLivePage();

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
    const fetchSpy = makeFetchSpyWithGuidedSession(
      makeJsonResponse(makePublicMatchDetailResponse()),
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
      ),
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
      ),
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
    setStoredSession();
    renderHumanMatchLivePage();

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitMessage(makeJoinableAllianceEnvelope(144));

    fireEvent.change(await screen.findByLabelText("Alliance action"), { target: { value: "create" } });
    fireEvent.change(screen.getByLabelText("Alliance name"), { target: { value: "Blue League" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit alliance" }));

    await waitFor(() => {
      expectFetchCall(fetchSpy, "http://127.0.0.1:8000/api/v1/matches/match-alpha/alliances", {
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
      }, 1);
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
      expectFetchCall(fetchSpy, "http://127.0.0.1:8000/api/v1/matches/match-alpha/alliances", {
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
      }, 2);
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
      expectFetchCall(fetchSpy, "http://127.0.0.1:8000/api/v1/matches/match-alpha/alliances", {
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
      }, 3);
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
    const fetchSpy = makeFetchSpyWithGuidedSession(
      makeJsonResponse(makePublicMatchDetailResponse()),
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
    setStoredSession();
    renderHumanMatchLivePage();

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
    const fetchSpy = makeFetchSpyWithGuidedSession(
      makeJsonResponse(makePublicMatchDetailResponse()),
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
    setStoredSession();
    renderHumanMatchLivePage();

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
});
