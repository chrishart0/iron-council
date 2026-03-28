from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResourceState(StrictModel):
    food: int = Field(ge=0)
    production: int = Field(ge=0)
    money: int = Field(ge=0)


class CityUpgradeState(StrictModel):
    economy: int = Field(ge=0, le=3)
    military: int = Field(ge=0, le=3)
    fortification: int = Field(ge=0, le=3)


class BuildingQueueItem(StrictModel):
    type: Literal["economy", "military", "fortification"]
    tier: int = Field(ge=1, le=3)
    ticks_remaining: int = Field(ge=0)


class CityState(StrictModel):
    owner: str | None = None
    population: int = Field(ge=0)
    resources: ResourceState
    upgrades: CityUpgradeState
    garrison: int = Field(ge=0)
    building_queue: list[BuildingQueueItem] = Field(default_factory=list)


class ArmyState(StrictModel):
    id: str
    owner: str
    troops: int = Field(gt=0)
    location: str | None = None
    destination: str | None = None
    path: list[str] | None = None
    ticks_remaining: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_positioning(self) -> "ArmyState":
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
    cities_held: int = Field(ge=0)
    threshold: int = Field(ge=0)
    countdown_ticks_remaining: int | None = Field(default=None, ge=0)


class MatchState(StrictModel):
    tick: int = Field(ge=0)
    cities: dict[str, CityState]
    armies: list[ArmyState] = Field(default_factory=list)
    players: dict[str, PlayerState]
    victory: VictoryState
