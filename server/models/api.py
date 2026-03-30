from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from server.models.domain import MatchStatus, StrictModel, TickDuration
from server.models.fog import AgentStateProjection
from server.models.orders import OrderBatch


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


class MatchHistoryEntry(StrictModel):
    tick: TickDuration


class MatchHistoryResponse(StrictModel):
    match_id: str
    status: MatchStatus
    current_tick: TickDuration
    tick_interval_seconds: int = Field(gt=0)
    history: list[MatchHistoryEntry] = Field(default_factory=list)


class MatchReplayTickResponse(StrictModel):
    match_id: str
    tick: TickDuration
    state_snapshot: dict[str, Any]
    orders: dict[str, Any]
    events: dict[str, Any] | list[dict[str, Any]]


CompetitorKind = Literal["human", "agent"]


class LeaderboardEntry(StrictModel):
    rank: int = Field(ge=1)
    display_name: str
    competitor_kind: CompetitorKind
    elo: int = Field(ge=0)
    provisional: bool
    matches_played: int = Field(ge=0)
    wins: int = Field(ge=0)
    losses: int = Field(ge=0)
    draws: int = Field(ge=0)


class PublicLeaderboardResponse(StrictModel):
    leaderboard: list[LeaderboardEntry] = Field(default_factory=list)


class CompletedMatchSummary(StrictModel):
    match_id: str
    map: str
    final_tick: TickDuration
    tick_interval_seconds: int = Field(gt=0)
    player_count: int = Field(ge=0)
    completed_at: datetime
    winning_alliance_name: str | None = None
    winning_player_display_names: list[str] = Field(default_factory=list)


class CompletedMatchSummaryListResponse(StrictModel):
    matches: list[CompletedMatchSummary] = Field(default_factory=list)


class OrderAcceptanceResponse(StrictModel):
    status: Literal["accepted"]
    match_id: str
    player_id: str
    tick: TickDuration
    submission_index: int = Field(ge=0)


class MatchJoinRequest(StrictModel):
    match_id: str


class AuthenticatedOrderSubmissionRequest(StrictModel):
    match_id: str
    tick: TickDuration
    orders: OrderBatch


class MatchJoinResponse(StrictModel):
    status: Literal["accepted"]
    match_id: str
    agent_id: str
    player_id: str


class AgentProfileRating(StrictModel):
    elo: int = Field(ge=0)
    provisional: bool


class AgentProfileHistory(StrictModel):
    matches_played: int = Field(ge=0)
    wins: int = Field(ge=0)
    losses: int = Field(ge=0)
    draws: int = Field(ge=0)


class AgentProfileResponse(StrictModel):
    agent_id: str
    display_name: str
    is_seeded: bool
    rating: AgentProfileRating
    history: AgentProfileHistory


class AuthenticatedAgentContext(StrictModel):
    agent_id: str
    display_name: str
    is_seeded: bool


MessageChannel = Literal["world", "direct"]
CommandMessageChannel = Literal["world", "direct", "group"]
TreatyAction = Literal["propose", "accept", "withdraw"]
TreatyType = Literal["non_aggression", "defensive", "trade"]
TreatyStatus = Literal["proposed", "active", "withdrawn"]
AllianceAction = Literal["create", "join", "leave"]


class MatchMessageCreateRequest(StrictModel):
    match_id: str
    tick: TickDuration
    channel: MessageChannel
    recipient_id: str | None = None
    content: str = Field(min_length=1)


class MatchMessageRecord(StrictModel):
    message_id: int = Field(ge=0)
    channel: MessageChannel
    sender_id: str
    recipient_id: str | None = None
    tick: TickDuration
    content: str


class MatchMessageInboxResponse(StrictModel):
    match_id: str
    player_id: str
    messages: list[MatchMessageRecord] = Field(default_factory=list)


class MessageAcceptanceResponse(StrictModel):
    status: Literal["accepted"]
    match_id: str
    message_id: int = Field(ge=0)
    channel: MessageChannel
    sender_id: str
    recipient_id: str | None = None
    tick: TickDuration
    content: str


class GroupChatCreateRequest(StrictModel):
    match_id: str
    tick: TickDuration
    name: str = Field(min_length=1)
    member_ids: list[str] = Field(min_length=1)


class GroupChatRecord(StrictModel):
    group_chat_id: str
    name: str
    member_ids: list[str] = Field(default_factory=list)
    created_by: str
    created_tick: TickDuration


class GroupChatListResponse(StrictModel):
    match_id: str
    player_id: str
    group_chats: list[GroupChatRecord] = Field(default_factory=list)


class GroupChatCreateAcceptanceResponse(StrictModel):
    status: Literal["accepted"]
    match_id: str
    group_chat: GroupChatRecord


class GroupChatMessageCreateRequest(StrictModel):
    match_id: str
    tick: TickDuration
    content: str = Field(min_length=1)


class GroupChatMessageRecord(StrictModel):
    message_id: int = Field(ge=0)
    group_chat_id: str
    sender_id: str
    tick: TickDuration
    content: str


class GroupChatMessageListResponse(StrictModel):
    match_id: str
    group_chat_id: str
    player_id: str
    messages: list[GroupChatMessageRecord] = Field(default_factory=list)


class GroupChatMessageAcceptanceResponse(StrictModel):
    status: Literal["accepted"]
    match_id: str
    group_chat_id: str
    message: GroupChatMessageRecord


class TreatyActionRequest(StrictModel):
    match_id: str
    counterparty_id: str
    action: TreatyAction
    treaty_type: TreatyType


class TreatyRecord(StrictModel):
    treaty_id: int = Field(ge=0)
    player_a_id: str
    player_b_id: str
    treaty_type: TreatyType
    status: TreatyStatus
    proposed_by: str
    proposed_tick: TickDuration
    signed_tick: TickDuration | None = None
    withdrawn_by: str | None = None
    withdrawn_tick: TickDuration | None = None


class TreatyListResponse(StrictModel):
    match_id: str
    treaties: list[TreatyRecord] = Field(default_factory=list)


class TreatyActionAcceptanceResponse(StrictModel):
    status: Literal["accepted"]
    match_id: str
    treaty: TreatyRecord


class AllianceActionRequest(StrictModel):
    match_id: str
    action: AllianceAction
    alliance_id: str | None = None
    name: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_action_fields(self) -> AllianceActionRequest:
        if self.action == "create":
            if self.alliance_id is not None:
                raise ValueError("alliance create does not accept alliance_id")
            if self.name is None:
                raise ValueError("alliance create requires name")
            return self

        if self.action == "join":
            if self.alliance_id is None:
                raise ValueError("alliance join requires alliance_id")
            if self.name is not None:
                raise ValueError("alliance join does not accept name")
            return self

        if self.alliance_id is not None:
            raise ValueError("alliance leave does not accept alliance_id")
        if self.name is not None:
            raise ValueError("alliance leave does not accept name")
        return self


class AllianceMemberRecord(StrictModel):
    player_id: str
    joined_tick: TickDuration


class AllianceRecord(StrictModel):
    alliance_id: str
    name: str
    leader_id: str
    formed_tick: TickDuration
    members: list[AllianceMemberRecord] = Field(default_factory=list)


class AllianceListResponse(StrictModel):
    match_id: str
    alliances: list[AllianceRecord] = Field(default_factory=list)


class AllianceActionAcceptanceResponse(StrictModel):
    status: Literal["accepted"]
    match_id: str
    player_id: str
    alliance: AllianceRecord | None = None


class AgentCommandMessage(StrictModel):
    channel: CommandMessageChannel
    recipient_id: str | None = None
    group_chat_id: str | None = None
    content: str = Field(min_length=1)


class AgentCommandTreaty(StrictModel):
    counterparty_id: str
    action: TreatyAction
    treaty_type: TreatyType


class AgentCommandAllianceAction(StrictModel):
    action: AllianceAction
    alliance_id: str | None = None
    name: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_action_fields(self) -> AgentCommandAllianceAction:
        if self.action == "create":
            if self.alliance_id is not None:
                raise ValueError("alliance create does not accept alliance_id")
            if self.name is None:
                raise ValueError("alliance create requires name")
            return self

        if self.action == "join":
            if self.alliance_id is None:
                raise ValueError("alliance join requires alliance_id")
            if self.name is not None:
                raise ValueError("alliance join does not accept name")
            return self

        if self.alliance_id is not None:
            raise ValueError("alliance leave does not accept alliance_id")
        if self.name is not None:
            raise ValueError("alliance leave does not accept name")
        return self


class AgentCommandEnvelopeRequest(StrictModel):
    match_id: str
    tick: TickDuration
    orders: OrderBatch = Field(default_factory=OrderBatch)
    messages: list[AgentCommandMessage] = Field(default_factory=list)
    treaties: list[AgentCommandTreaty] = Field(default_factory=list)
    alliance: AgentCommandAllianceAction | None = None


class AgentCommandEnvelopeResponse(StrictModel):
    status: Literal["accepted"]
    match_id: str
    player_id: str
    tick: TickDuration
    orders: OrderAcceptanceResponse | None = None
    messages: list[MessageAcceptanceResponse | GroupChatMessageAcceptanceResponse] = Field(
        default_factory=list
    )
    treaties: list[TreatyActionAcceptanceResponse] = Field(default_factory=list)
    alliance: AllianceActionAcceptanceResponse | None = None


class AgentBriefingMessageBuckets(StrictModel):
    direct: list[MatchMessageRecord] = Field(default_factory=list)
    group: list[GroupChatMessageRecord] = Field(default_factory=list)
    world: list[MatchMessageRecord] = Field(default_factory=list)


class AgentBriefingResponse(StrictModel):
    match_id: str
    player_id: str
    state: AgentStateProjection
    alliances: list[AllianceRecord] = Field(default_factory=list)
    treaties: list[TreatyRecord] = Field(default_factory=list)
    group_chats: list[GroupChatRecord] = Field(default_factory=list)
    messages: AgentBriefingMessageBuckets
