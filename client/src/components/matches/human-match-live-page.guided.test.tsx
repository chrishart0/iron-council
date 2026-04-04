import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  expectFetchCall,
  makeEnvelope,
  makeGuidedSessionResponse,
  makeHumanEnvelope,
  makeHumanOwnedAgentMatchDetailResponse,
  makeJsonResponse,
  makeOwnedApiKeysResponse,
  MockWebSocket,
  renderHumanMatchLivePage,
  setStoredSession
} from "./human-match-live-page-test-helpers";

describe("HumanMatchLivePage guided controls", () => {
  it("refreshes guided-session after guided writes and keeps websocket state authoritative", async () => {
    setStoredSession();

    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce(makeJsonResponse(makeHumanOwnedAgentMatchDetailResponse()))
      .mockResolvedValueOnce(makeJsonResponse(makeOwnedApiKeysResponse()))
      .mockResolvedValueOnce(makeJsonResponse(makeGuidedSessionResponse()))
      .mockResolvedValueOnce(
        makeJsonResponse(
          {
            status: "accepted",
            guidance_id: "guidance-8",
            match_id: "match-alpha",
            agent_id: "agent-player-2",
            player_id: "player-2",
            tick: 144,
            content: "Commit the drafted move."
          },
          202
        )
      )
      .mockResolvedValueOnce(
        makeJsonResponse(
          makeGuidedSessionResponse({
            guidanceContent: "Commit the drafted move.",
            queuedDestination: "york"
          })
        )
      )
      .mockResolvedValueOnce(
        makeJsonResponse(
          {
            status: "accepted",
            override_id: "override-3",
            match_id: "match-alpha",
            agent_id: "agent-player-2",
            player_id: "player-2",
            tick: 144,
            submission_index: 1,
            superseded_submission_count: 0,
            orders: {
              movements: [{ army_id: "army-1", destination: "leeds" }],
              recruitment: [],
              upgrades: [],
              transfers: []
            }
          },
          202
        )
      )
      .mockResolvedValueOnce(
        makeJsonResponse(
          makeGuidedSessionResponse({
            guidanceContent: "Commit the drafted move.",
            queuedDestination: "leeds"
          })
        )
      );

    vi.stubGlobal("fetch", fetchSpy);
    renderHumanMatchLivePage();

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitOpen();
    MockWebSocket.instances[0]?.emitMessage(makeHumanEnvelope(144));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Guided agent controls" })).toBeVisible();
    });

    expect(screen.getByText("Queued orders")).toBeVisible();
    expect(screen.getByText("army-1 -> york")).toBeVisible();
    expect(screen.getByText("Hold the north.")).toBeVisible();
    expect(screen.getByText("player-2 at leeds with 5 troops (full)")).toBeVisible();

    fireEvent.change(screen.getByLabelText("Guidance message"), {
      target: { value: "Commit the drafted move." }
    });
    fireEvent.click(screen.getByRole("button", { name: "Send guidance" }));

    await waitFor(() => {
      expect(screen.getByText("Guidance accepted for tick 144.")).toBeVisible();
    });

    fireEvent.click(screen.getByRole("button", { name: "Add movement order" }));
    fireEvent.change(screen.getByLabelText("Movement army ID 1"), {
      target: { value: "army-1" }
    });
    fireEvent.change(screen.getByLabelText("Movement destination 1"), {
      target: { value: "leeds" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit guided override" }));

    await waitFor(() => {
      expect(screen.getByText("Guided override accepted for tick 144.")).toBeVisible();
    });

    await waitFor(() => {
      expect(screen.getByText("army-1 -> leeds")).toBeVisible();
    });
    expect(screen.getByText("Commit the drafted move.")).toBeVisible();
    expect(screen.getByText("player-2 at leeds with 5 troops (full)")).toBeVisible();

    expectFetchCall(fetchSpy, "http://127.0.0.1:8000/api/v1/account/api-keys", {
      cache: "no-store",
      headers: {
        accept: "application/json",
        authorization: "Bearer human-jwt"
      }
    });
    expectFetchCall(fetchSpy, "http://127.0.0.1:8000/api/v1/matches/match-alpha/agents/agent-player-2/guided-session", {
      cache: "no-store",
      headers: {
        accept: "application/json",
        authorization: "Bearer human-jwt"
      }
    }, 1);
    expectFetchCall(fetchSpy, "http://127.0.0.1:8000/api/v1/matches/match-alpha/agents/agent-player-2/guidance", {
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
        content: "Commit the drafted move."
      })
    });
    expectFetchCall(fetchSpy, "http://127.0.0.1:8000/api/v1/matches/match-alpha/agents/agent-player-2/override", {
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
        }
      })
    });
    expectFetchCall(fetchSpy, "http://127.0.0.1:8000/api/v1/matches/match-alpha/agents/agent-player-2/guided-session", {
      cache: "no-store",
      headers: {
        accept: "application/json",
        authorization: "Bearer human-jwt"
      }
    }, 2);
    expectFetchCall(fetchSpy, "http://127.0.0.1:8000/api/v1/matches/match-alpha/agents/agent-player-2/guided-session", {
      cache: "no-store",
      headers: {
        accept: "application/json",
        authorization: "Bearer human-jwt"
      }
    }, 3);
  });

  it("refreshes guided-session when the websocket tick advances", async () => {
    setStoredSession();

    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce(makeJsonResponse(makeHumanOwnedAgentMatchDetailResponse()))
      .mockResolvedValueOnce(makeJsonResponse(makeOwnedApiKeysResponse()))
      .mockResolvedValueOnce(makeJsonResponse(makeGuidedSessionResponse()))
      .mockResolvedValueOnce(
        makeJsonResponse(
          makeGuidedSessionResponse({
            guidanceContent: "Advance on the western road.",
            queuedDestination: "leeds"
          })
        )
      );

    vi.stubGlobal("fetch", fetchSpy);
    renderHumanMatchLivePage();

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitOpen();
    MockWebSocket.instances[0]?.emitMessage(makeHumanEnvelope(144));

    await waitFor(() => {
      expect(screen.getByText("army-1 -> york")).toBeVisible();
    });
    expect(screen.getByText("Hold the north.")).toBeVisible();

    MockWebSocket.instances[0]?.emitMessage(makeHumanEnvelope(145));

    await waitFor(() => {
      expect(screen.getByText("army-1 -> leeds")).toBeVisible();
    });
    expect(screen.getByText("Advance on the western road.")).toBeVisible();
    expect(screen.getByText("player-2 at manchester with 5 troops (full)")).toBeVisible();

    expectFetchCall(fetchSpy, "http://127.0.0.1:8000/api/v1/account/api-keys", {
      cache: "no-store",
      headers: {
        accept: "application/json",
        authorization: "Bearer human-jwt"
      }
    });
    expectFetchCall(fetchSpy, "http://127.0.0.1:8000/api/v1/matches/match-alpha/agents/agent-player-2/guided-session", {
      cache: "no-store",
      headers: {
        accept: "application/json",
        authorization: "Bearer human-jwt"
      }
    }, 1);
    expectFetchCall(fetchSpy, "http://127.0.0.1:8000/api/v1/matches/match-alpha/agents/agent-player-2/guided-session", {
      cache: "no-store",
      headers: {
        accept: "application/json",
        authorization: "Bearer human-jwt"
      }
    }, 2);
  });

  it("preserves guided drafts and shows structured browser-boundary guided errors", async () => {
    setStoredSession();

    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce(makeJsonResponse(makeHumanOwnedAgentMatchDetailResponse()))
      .mockResolvedValueOnce(makeJsonResponse(makeOwnedApiKeysResponse()))
      .mockResolvedValueOnce(makeJsonResponse(makeGuidedSessionResponse()))
      .mockResolvedValueOnce(
        makeJsonResponse(
          {
            error: {
              code: "tick_mismatch",
              message: "Guidance payload tick '143' does not match current match tick '144'."
            }
          },
          409
        )
      )
      .mockResolvedValueOnce(
        makeJsonResponse(
          {
            error: {
              code: "tick_mismatch",
              message: "Override payload tick '143' does not match current match tick '144'."
            }
          },
          409
        )
      );

    vi.stubGlobal("fetch", fetchSpy);
    renderHumanMatchLivePage();

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitOpen();
    MockWebSocket.instances[0]?.emitMessage(makeHumanEnvelope(144));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Guided agent controls" })).toBeVisible();
    });

    fireEvent.change(screen.getByLabelText("Guidance message"), {
      target: { value: "Keep pressure on York." }
    });
    fireEvent.click(screen.getByRole("button", { name: "Send guidance" }));

    await waitFor(() => {
      expect(screen.getByText("Guidance payload tick '143' does not match current match tick '144'.")).toBeVisible();
    });
    expect(screen.getByText("Error code: tick_mismatch")).toBeVisible();
    expect(screen.getAllByText("HTTP status: 409").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Guidance message")).toHaveValue("Keep pressure on York.");

    fireEvent.click(screen.getByRole("button", { name: "Add movement order" }));
    fireEvent.change(screen.getByLabelText("Movement army ID 1"), {
      target: { value: "army-1" }
    });
    fireEvent.change(screen.getByLabelText("Movement destination 1"), {
      target: { value: "leeds" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit guided override" }));

    await waitFor(() => {
      expect(screen.getByText("Override payload tick '143' does not match current match tick '144'.")).toBeVisible();
    });
    expect(screen.getAllByText("Error code: tick_mismatch").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("HTTP status: 409").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByLabelText("Movement army ID 1")).toHaveValue("army-1");
    expect(screen.getByLabelText("Movement destination 1")).toHaveValue("leeds");

    expectFetchCall(fetchSpy, "http://127.0.0.1:8000/api/v1/account/api-keys", {
      cache: "no-store",
      headers: {
        accept: "application/json",
        authorization: "Bearer human-jwt"
      }
    });
    expectFetchCall(fetchSpy, "http://127.0.0.1:8000/api/v1/matches/match-alpha/agents/agent-player-2/guidance", {
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
        content: "Keep pressure on York."
      })
    });
    expectFetchCall(fetchSpy, "http://127.0.0.1:8000/api/v1/matches/match-alpha/agents/agent-player-2/override", {
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
        }
      })
    });
  });

  it("resolves guided controls from owned agent ids instead of the websocket player slot", async () => {
    setStoredSession();

    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce(makeJsonResponse(makeHumanOwnedAgentMatchDetailResponse()))
      .mockResolvedValueOnce(makeJsonResponse(makeOwnedApiKeysResponse()))
      .mockResolvedValueOnce(makeJsonResponse(makeGuidedSessionResponse()));

    vi.stubGlobal("fetch", fetchSpy);
    renderHumanMatchLivePage();

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitOpen();
    MockWebSocket.instances[0]?.emitMessage(makeHumanEnvelope(144));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Guided agent controls" })).toBeVisible();
    });

    expect(screen.getByText("Hold the north.")).toBeVisible();
    expectFetchCall(fetchSpy, "http://127.0.0.1:8000/api/v1/account/api-keys", {
      cache: "no-store",
      headers: {
        accept: "application/json",
        authorization: "Bearer human-jwt"
      }
    });
    expectFetchCall(fetchSpy, "http://127.0.0.1:8000/api/v1/matches/match-alpha/agents/agent-player-2/guided-session", {
      cache: "no-store",
      headers: {
        accept: "application/json",
        authorization: "Bearer human-jwt"
      }
    });
  });
});
