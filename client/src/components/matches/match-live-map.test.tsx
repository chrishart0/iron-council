import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
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
            visibility: "full",
            visibleLocationCityId: "manchester",
            transit: {
              status: "stationary",
              ticksRemaining: 0,
              destinationCityId: null,
              pathCityIds: null
            }
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
            visibility: "partial",
            visibleLocationCityId: null,
            transit: {
              status: "in_transit",
              ticksRemaining: 2,
              destinationCityId: null,
              pathCityIds: null
            }
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

  it("supports keyboard activation and pressed state for selectable city and army markers", () => {
    const onCitySelect = vi.fn();
    const onArmySelect = vi.fn();

    render(
      <MatchLiveMap
        mapLayout={loadBritainMapLayout()}
        liveStatus="live"
        tick={143}
        perspective="player"
        selectedCityId="manchester"
        selectedArmyId="army-1"
        onCitySelect={onCitySelect}
        onArmySelect={onArmySelect}
        cities={[
          {
            cityId: "manchester",
            cityName: "Manchester",
            ownerLabel: "player-2",
            ownerVisibility: "full",
            garrisonLabel: "7"
          }
        ]}
        armies={[
          {
            armyId: "army-1",
            cityId: "manchester",
            cityName: "Manchester",
            ownerLabel: "player-2",
            troopsLabel: "5",
            visibility: "full",
            visibleLocationCityId: "manchester",
            transit: {
              status: "stationary",
              ticksRemaining: 0,
              destinationCityId: null,
              pathCityIds: null
            }
          }
        ]}
      />
    );

    const cityButton = screen.getByRole("button", { name: "Select city Manchester" });
    const armyButton = screen.getByRole("button", { name: "Select army army-1 at Manchester" });

    expect(cityButton).toHaveAttribute("aria-pressed", "true");
    expect(armyButton).toHaveAttribute("aria-pressed", "true");

    fireEvent.keyDown(cityButton, { key: "Enter" });
    fireEvent.keyDown(armyButton, { key: " " });

    expect(onCitySelect).toHaveBeenCalledTimes(1);
    expect(onCitySelect).toHaveBeenCalledWith(
      expect.objectContaining({ cityId: "manchester" })
    );
    expect(onArmySelect).toHaveBeenCalledTimes(1);
    expect(onArmySelect).toHaveBeenCalledWith(
      expect.objectContaining({ armyId: "army-1" })
    );
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

  it("renders deterministic spectator transit overlays and readable marching ETA copy from visible route fields", () => {
    render(
      <MatchLiveMap
        mapLayout={loadBritainMapLayout()}
        liveStatus="live"
        tick={143}
        perspective="spectator"
        cities={[
          {
            cityId: "manchester",
            cityName: "Manchester",
            ownerLabel: "Arthur",
            ownerVisibility: "full",
            garrisonLabel: "7"
          },
          {
            cityId: "leeds",
            cityName: "Leeds",
            ownerLabel: "Arthur",
            ownerVisibility: "full",
            garrisonLabel: "3"
          }
        ]}
        armies={[
          {
            armyId: "army-transit",
            cityId: "manchester",
            cityName: "Manchester",
            ownerLabel: "Arthur",
            troopsLabel: "9",
            visibility: "full",
            visibleLocationCityId: "manchester",
            transit: {
              status: "in_transit",
              ticksRemaining: 3,
              destinationCityId: "leeds",
              pathCityIds: ["manchester", "leeds"]
            }
          }
        ]}
      />
    );

    const mapRegion = screen.getByRole("region", { name: "Britain strategic map" });
    expect(
      within(mapRegion).getByLabelText("Transit indicator Arthur Leeds ETA 3 ticks")
    ).toBeVisible();
    expect(
      within(mapRegion).getByText("Arthur marching on Leeds • ETA 3 ticks")
    ).toBeVisible();
  });

  it("keeps player transit summaries fog-safe when route details are hidden", () => {
    render(
      <MatchLiveMap
        mapLayout={loadBritainMapLayout()}
        liveStatus="live"
        tick={143}
        perspective="player"
        cities={[
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
            armyId: "army-hidden-transit",
            cityId: "birmingham",
            cityName: "Birmingham",
            ownerLabel: "player-3",
            troopsLabel: null,
            visibility: "partial",
            visibleLocationCityId: null,
            transit: {
              status: "in_transit",
              ticksRemaining: 2,
              destinationCityId: null,
              pathCityIds: null
            }
          }
        ]}
      />
    );

    const mapRegion = screen.getByRole("region", { name: "Britain strategic map" });
    expect(
      within(mapRegion).queryByLabelText(/Transit overlay player-3/i)
    ).not.toBeInTheDocument();
    expect(
      within(mapRegion).getByText("player-3 march in progress • ETA 2 ticks")
    ).toBeVisible();
    expect(within(mapRegion).queryByText(/Birmingham to/i)).not.toBeInTheDocument();
  });

  it("suppresses stale transit overlays when the feed is offline and shows the offline explanatory state", () => {
    render(
      <MatchLiveMap
        mapLayout={loadBritainMapLayout()}
        liveStatus="not_live"
        tick={143}
        perspective="spectator"
        cities={[
          {
            cityId: "manchester",
            cityName: "Manchester",
            ownerLabel: "Arthur",
            ownerVisibility: "full",
            garrisonLabel: "7"
          },
          {
            cityId: "leeds",
            cityName: "Leeds",
            ownerLabel: "Arthur",
            ownerVisibility: "full",
            garrisonLabel: "3"
          }
        ]}
        armies={[
          {
            armyId: "army-transit",
            cityId: "manchester",
            cityName: "Manchester",
            ownerLabel: "Arthur",
            troopsLabel: "9",
            visibility: "full",
            visibleLocationCityId: "manchester",
            transit: {
              status: "in_transit",
              ticksRemaining: 3,
              destinationCityId: "leeds",
              pathCityIds: ["manchester", "leeds"]
            }
          }
        ]}
      />
    );

    const mapRegion = screen.getByRole("region", { name: "Britain strategic map" });
    expect(within(mapRegion).queryByLabelText("Transit indicator Arthur Leeds ETA 3 ticks")).not.toBeInTheDocument();
    expect(within(mapRegion).queryByText("Arthur marching on Leeds • ETA 3 ticks")).not.toBeInTheDocument();
    expect(within(mapRegion).getByText("No visible transit overlays in the last confirmed update.")).toBeVisible();
  });

  it("renders deterministic transit empty messaging when no visible overlays exist", () => {
    render(
      <MatchLiveMap
        mapLayout={loadBritainMapLayout()}
        liveStatus="live"
        tick={143}
        perspective="spectator"
        cities={[]}
        armies={[]}
      />
    );

    const mapRegion = screen.getByRole("region", { name: "Britain strategic map" });
    expect(within(mapRegion).getByText("No visible transit overlays in this update.")).toBeVisible();
  });
});
