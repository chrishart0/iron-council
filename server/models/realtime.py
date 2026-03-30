from __future__ import annotations

from typing import Literal

from pydantic import Field

from server.models.api import AllianceRecord, MatchMessageRecord, TreatyRecord
from server.models.domain import StrictModel
from server.models.fog import AgentStateProjection
from server.models.state import ArmyState, CityState, PlayerState, VictoryState

RealtimeViewerRole = Literal["player", "spectator"]


class SpectatorStateProjection(StrictModel):
    match_id: str
    tick: int
    cities: dict[str, CityState]
    armies: list[ArmyState] = Field(default_factory=list)
    players: dict[str, PlayerState]
    victory: VictoryState


class MatchRealtimePayload(StrictModel):
    match_id: str
    viewer_role: RealtimeViewerRole
    player_id: str | None = None
    state: AgentStateProjection | SpectatorStateProjection
    world_messages: list[MatchMessageRecord] = Field(default_factory=list)
    treaties: list[TreatyRecord] = Field(default_factory=list)
    alliances: list[AllianceRecord] = Field(default_factory=list)


class MatchRealtimeEnvelope(StrictModel):
    type: Literal["tick_update"]
    data: MatchRealtimePayload
