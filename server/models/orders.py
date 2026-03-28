from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MovementOrder(StrictModel):
    type: Literal["movement"] = "movement"
    army_id: str
    destination: str


class RecruitmentOrder(StrictModel):
    type: Literal["recruitment"] = "recruitment"
    city: str
    troops: int = Field(gt=0)


class UpgradeOrder(StrictModel):
    type: Literal["upgrade"] = "upgrade"
    city: str
    track: Literal["economy", "military", "fortification"]
    target_tier: int = Field(ge=1, le=3)


class TransferOrder(StrictModel):
    type: Literal["transfer"] = "transfer"
    to: str
    resource: Literal["food", "production", "money"]
    amount: int = Field(gt=0)


class OrderBatch(StrictModel):
    movements: list[MovementOrder] = Field(default_factory=list)
    recruitment: list[RecruitmentOrder] = Field(default_factory=list)
    upgrades: list[UpgradeOrder] = Field(default_factory=list)
    transfers: list[TransferOrder] = Field(default_factory=list)


class OrderEnvelope(StrictModel):
    match_id: str
    player_id: str
    tick: int = Field(ge=0)
    orders: OrderBatch
