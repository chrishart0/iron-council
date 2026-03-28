from __future__ import annotations

from pydantic import Field, model_validator

from server.models.domain import (
    FortificationTier,
    NonNegativeCount,
    PositiveCount,
    PositiveTickDuration,
    StrictModel,
    TickDuration,
    UpgradeTrack,
)


class ResourceState(StrictModel):
    food: NonNegativeCount
    production: NonNegativeCount
    money: NonNegativeCount


class CityUpgradeState(StrictModel):
    economy: NonNegativeCount = Field(le=3)
    military: NonNegativeCount = Field(le=3)
    fortification: NonNegativeCount = Field(le=3)


class BuildingQueueItem(StrictModel):
    type: UpgradeTrack
    tier: FortificationTier
    ticks_remaining: PositiveTickDuration


class CityState(StrictModel):
    owner: str | None = None
    population: NonNegativeCount
    resources: ResourceState
    upgrades: CityUpgradeState
    garrison: NonNegativeCount
    building_queue: list[BuildingQueueItem] = Field(default_factory=list)


class ArmyState(StrictModel):
    id: str
    owner: str
    troops: PositiveCount
    location: str | None = None
    destination: str | None = None
    path: list[str] | None = None
    ticks_remaining: TickDuration

    @model_validator(mode="after")
    def validate_positioning(self) -> ArmyState:
        if self.destination is None:
            if self.path is not None:
                raise ValueError("path must be null when destination is null")
            return self

        if not self.path:
            raise ValueError("path is required when destination is set")
        if self.ticks_remaining == 0:
            raise ValueError("ticks_remaining must be positive while in transit")
        return self


class PlayerState(StrictModel):
    resources: ResourceState
    cities_owned: list[str] = Field(default_factory=list)
    alliance_id: str | None = None
    is_eliminated: bool = False


class VictoryState(StrictModel):
    leading_alliance: str | None = None
    cities_held: NonNegativeCount
    threshold: NonNegativeCount
    countdown_ticks_remaining: TickDuration | None = None


class MatchState(StrictModel):
    tick: NonNegativeCount
    cities: dict[str, CityState]
    armies: list[ArmyState] = Field(default_factory=list)
    players: dict[str, PlayerState]
    victory: VictoryState
