from __future__ import annotations

from typing import Literal

from pydantic import Field

from server.models.domain import (
    FortificationTier,
    PositiveCount,
    ResourceType,
    StrictModel,
    TickDuration,
    UpgradeTrack,
)


class MovementOrder(StrictModel):
    type: Literal["movement"] = Field(default="movement", exclude=True)
    army_id: str
    destination: str


class RecruitmentOrder(StrictModel):
    type: Literal["recruitment"] = Field(default="recruitment", exclude=True)
    city: str
    troops: PositiveCount


class UpgradeOrder(StrictModel):
    type: Literal["upgrade"] = Field(default="upgrade", exclude=True)
    city: str
    track: UpgradeTrack
    target_tier: FortificationTier


class TransferOrder(StrictModel):
    type: Literal["transfer"] = Field(default="transfer", exclude=True)
    to: str
    resource: ResourceType
    amount: PositiveCount


class OrderBatch(StrictModel):
    movements: list[MovementOrder] = Field(default_factory=list)
    recruitment: list[RecruitmentOrder] = Field(default_factory=list)
    upgrades: list[UpgradeOrder] = Field(default_factory=list)
    transfers: list[TransferOrder] = Field(default_factory=list)


class OrderEnvelope(StrictModel):
    match_id: str
    player_id: str
    tick: TickDuration
    orders: OrderBatch
