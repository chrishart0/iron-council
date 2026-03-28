from __future__ import annotations

from typing import Literal

from pydantic import Field

from server.models.domain import PositiveCount, StrictModel, TickDuration
from server.models.state import BuildingQueueItem, CityUpgradeState, ResourceState, VictoryState

FogVisibility = Literal["full", "partial"]
UnknownField = Literal["unknown"]


class VisibleCityState(StrictModel):
    owner: str | None = None
    visibility: FogVisibility
    population: int | UnknownField
    resources: ResourceState | UnknownField
    upgrades: CityUpgradeState | UnknownField
    garrison: int | UnknownField
    building_queue: list[BuildingQueueItem] | UnknownField = Field(default_factory=list)


class VisibleArmyState(StrictModel):
    id: str
    owner: str
    visibility: FogVisibility
    troops: PositiveCount | UnknownField
    location: str | None = None
    destination: str | None = None
    path: list[str] | UnknownField | None = None
    ticks_remaining: TickDuration


class AgentStateProjection(StrictModel):
    match_id: str
    tick: int
    player_id: str
    resources: ResourceState
    cities: dict[str, VisibleCityState]
    visible_armies: list[VisibleArmyState] = Field(default_factory=list)
    alliance_id: str | None = None
    alliance_members: list[str] = Field(default_factory=list)
    victory: VictoryState
