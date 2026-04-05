import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  makeEnvelope,
  makeJoinableAllianceEnvelope,
  makePublicMatchDetailResponse,
} from "./human-match-live-page-fixtures";
import {
  expectFetchCall,
  makeFetchSpyWithGuidedSession,
  makeJsonResponse,
  MockWebSocket,
  renderHumanMatchLivePage,
  setStoredSession,
} from "./human-match-live-page-test-helpers";

describe("HumanMatchLivePage diplomacy", () => {
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
