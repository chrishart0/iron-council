from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

NonNegativeCount = Annotated[int, Field(ge=0)]
TickDuration = Annotated[int, Field(ge=0)]
PositiveCount = Annotated[int, Field(gt=0)]
PositiveTickDuration = Annotated[int, Field(gt=0)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResourceType(StrEnum):
    FOOD = "food"
    PRODUCTION = "production"
    MONEY = "money"


class MatchStatus(StrEnum):
    LOBBY = "lobby"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class UpgradeTrack(StrEnum):
    ECONOMY = "economy"
    MILITARY = "military"
    FORTIFICATION = "fortification"


class FortificationTier(IntEnum):
    NONE = 0
    TRENCHES = 1
    BUNKERS = 2
    FORTRESS = 3
