import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  makeEnvelope,
  makePublicMatchDetailResponse,
  makeSoloVisibleEnvelope,
} from "./human-match-live-page-fixtures";
import {
  expectFetchCall,
  makeFetchSpyWithGuidedSession,
  makeJsonResponse,
  MockWebSocket,
  renderHumanMatchLivePage,
  setStoredSession,
} from "./human-match-live-page-test-helpers";

describe("HumanMatchLivePage group chats", () => {
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

});
