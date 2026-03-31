import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { loadBritainMapLayout } from "../../lib/britain-map";
import { MatchLiveMap } from "./match-live-map";

afterEach(() => {
  cleanup();
});

describe("MatchLiveMap", () => {
  it("renders the canonical Britain strategic map with spectator-visible ownership and army overlays", () => {
    render(
      <MatchLiveMap
        mapLayout={loadBritainMapLayout()}
        liveStatus="live"
        tick={143}
        perspective="spectator"
        cities={[
          {
            cityId: "birmingham",
            cityName: "Birmingham",
            ownerLabel: "Arthur",
            ownerVisibility: "full",
            garrisonLabel: "7"
          },
          {
            cityId: "manchester",
            cityName: "Manchester",
            ownerLabel: "Morgana",
            ownerVisibility: "full",
            garrisonLabel: "4"
          }
        ]}
        armies={[
          {
            armyId: "army-1",
            cityId: "manchester",
            cityName: "Manchester",
            ownerLabel: "Morgana",
            troopsLabel: "5",
            visibility: "full"
          }
        ]}
      />
    );

    const mapRegion = screen.getByRole("region", { name: "Britain strategic map" });
    expect(within(mapRegion).getByText("Tick 143")).toBeVisible();
    expect(within(mapRegion).getByText("Birmingham")).toBeVisible();
    expect(within(mapRegion).getByText("Arthur")).toBeVisible();
    expect(within(mapRegion).getByText("Garrison 7")).toBeVisible();
    expect(within(mapRegion).getByText("Morgana army 5 at Manchester")).toBeVisible();
  });

  it("masks partial player visibility and shows an explicit offline state without dropping the board", () => {
    render(
      <MatchLiveMap
        mapLayout={loadBritainMapLayout()}
        liveStatus="not_live"
        tick={143}
        perspective="player"
        cities={[
          {
            cityId: "manchester",
            cityName: "Manchester",
            ownerLabel: "player-2",
            ownerVisibility: "full",
            garrisonLabel: "7"
          },
          {
            cityId: "birmingham",
            cityName: "Birmingham",
            ownerLabel: null,
            ownerVisibility: "partial",
            garrisonLabel: null
          }
        ]}
        armies={[
          {
            armyId: "army-2",
            cityId: "birmingham",
            cityName: "Birmingham",
            ownerLabel: "player-3",
            troopsLabel: null,
            visibility: "partial"
          }
        ]}
      />
    );

    const mapRegion = screen.getByRole("region", { name: "Britain strategic map" });
    expect(within(mapRegion).getByText("Player feed offline")).toBeVisible();
    expect(within(mapRegion).getByText("Manchester")).toBeVisible();
    expect(within(mapRegion).getByText("Owner player-2")).toBeVisible();
    expect(within(mapRegion).getByText("Owner hidden")).toBeVisible();
    expect(within(mapRegion).getByText("Garrison hidden")).toBeVisible();
    expect(within(mapRegion).getByText("player-3 army hidden near Birmingham")).toBeVisible();
  });

  it("renders a deterministic empty state before the first live snapshot", () => {
    render(
      <MatchLiveMap
        mapLayout={loadBritainMapLayout()}
        liveStatus="live"
        tick={null}
        perspective="spectator"
        cities={[]}
        armies={[]}
      />
    );

    const mapRegion = screen.getByRole("region", { name: "Britain strategic map" });
    expect(within(mapRegion).getByText("No live strategic map data is available yet.")).toBeVisible();
    expect(within(mapRegion).getByText("London")).toBeVisible();
  });
});
