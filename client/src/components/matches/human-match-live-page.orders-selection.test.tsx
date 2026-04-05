import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  makeEnvelope,
  makeGuidedSessionResponse,
  makePublicMatchDetailResponse,
} from "./human-match-live-page-fixtures";
import {
  expectFetchCall,
  expectNoFetchCall,
  makeJsonResponse,
  MockWebSocket,
  renderHumanMatchLivePage,
  setStoredSession,
} from "./human-match-live-page-test-helpers";

describe("HumanMatchLivePage orders and map selection", () => {
  it("renders boring order drafts after the first live snapshot and allows adding and removing each order type", async () => {
    setStoredSession();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => makePublicMatchDetailResponse()
      })
    );

    renderHumanMatchLivePage();

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
    setStoredSession({
      apiBaseUrl: "https://hydrated.example/",
      bearerToken: "human-jwt"
    });

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

      if (url === "https://hydrated.example/api/v1/matches/match-alpha/agents/agent-player-2/guided-session") {
        return makeJsonResponse(makeGuidedSessionResponse());
      }

      throw new Error(`Unexpected fetch call: ${url} ${init?.method ?? "GET"}`);
    });

    vi.stubGlobal("fetch", fetchSpy);
    renderHumanMatchLivePage();

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
      expectFetchCall(fetchSpy, "https://hydrated.example/api/v1/matches/match-alpha/commands", {
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
    });
    expect(screen.getByText("Orders accepted for tick 144 from player-2.")).toBeVisible();
    expect(screen.queryByLabelText("Movement army ID 1")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Movement destination 1")).not.toBeInTheDocument();
  });

  it("blocks incomplete draft rows before submission and preserves the draft for correction", async () => {
    setStoredSession();
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => makePublicMatchDetailResponse()
    });

    vi.stubGlobal("fetch", fetchSpy);
    renderHumanMatchLivePage();

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
    expectNoFetchCall(fetchSpy, "http://127.0.0.1:8000/api/v1/matches/match-alpha/commands");
    expect(screen.getByLabelText("Recruitment city 1")).toHaveValue("manchester");
    expect(screen.getByLabelText("Recruitment troops 1")).toHaveValue(null);
  });

  it("preserves draft rows and shows structured command failure details when submission is rejected", async () => {
    setStoredSession();
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

      if (url === "http://127.0.0.1:8000/api/v1/matches/match-alpha/agents/agent-player-2/guided-session") {
        return makeJsonResponse(makeGuidedSessionResponse());
      }

      throw new Error(`Unexpected fetch call: ${url} ${init?.method ?? "GET"}`);
    });

    vi.stubGlobal("fetch", fetchSpy);
    renderHumanMatchLivePage();

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

    expectFetchCall(fetchSpy, "http://127.0.0.1:8000/api/v1/matches/match-alpha/commands", {
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
    setStoredSession();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => makePublicMatchDetailResponse()
      })
    );

    renderHumanMatchLivePage();

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
    setStoredSession();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => makePublicMatchDetailResponse()
      })
    );

    renderHumanMatchLivePage();

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

  it("clears stale selection helper guidance after a manual order draft interaction", async () => {
    setStoredSession();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => makePublicMatchDetailResponse()
      })
    );

    renderHumanMatchLivePage();

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    MockWebSocket.instances[0]?.emitOpen();
    MockWebSocket.instances[0]?.emitMessage(makeEnvelope(143));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Order Drafts" })).toBeVisible();
    });

    fireEvent.click(screen.getByRole("button", { name: "Add recruitment order" }));

    const partialArmyButton = screen.getByRole("button", { name: "Select army army-2 near Birmingham" });
    fireEvent.click(partialArmyButton);
    fireEvent.click(screen.getByRole("button", { name: "Use selected city for recruitment city 1" }));

    const inspectorRegion = screen.getByRole("region", { name: "Map selection inspector" });
    expect(within(inspectorRegion).getByRole("status")).toHaveTextContent(
      "Selection helper could not update recruitment city 1: the selected army does not expose a visible city."
    );

    fireEvent.change(screen.getByLabelText("Recruitment city 1"), {
      target: { value: "manchester" }
    });

    await waitFor(() => {
      expect(within(inspectorRegion).queryByRole("status")).not.toBeInTheDocument();
    });
  });
});
