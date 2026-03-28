from __future__ import annotations

from typing import Literal

from pydantic import Field

from server.models.domain import MatchStatus, StrictModel, TickDuration


class ApiErrorDetail(StrictModel):
    code: str
    message: str


class ApiErrorResponse(StrictModel):
    error: ApiErrorDetail


class MatchSummary(StrictModel):
    match_id: str
    status: MatchStatus
    tick: TickDuration
    tick_interval_seconds: int = Field(gt=0)


class MatchListResponse(StrictModel):
    matches: list[MatchSummary] = Field(default_factory=list)


class OrderAcceptanceResponse(StrictModel):
    status: Literal["accepted"]
    match_id: str
    player_id: str
    tick: TickDuration
    submission_index: int = Field(ge=0)
