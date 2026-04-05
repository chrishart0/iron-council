import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  makeEnvelope,
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

describe("HumanMatchLivePage messages", () => {
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

});
