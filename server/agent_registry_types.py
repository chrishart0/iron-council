from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from server.models.api import AgentProfileResponse, MessageChannel, TreatyStatus, TreatyType
from server.models.domain import MatchStatus
from server.models.orders import OrderEnvelope
from server.models.state import MatchState


@dataclass(slots=True)
class MatchMessage:
    message_id: int
    channel: MessageChannel
    sender_id: str
    recipient_id: str | None
    tick: int
    content: str


@dataclass(slots=True)
class MatchTreaty:
    treaty_id: int
    player_a_id: str
    player_b_id: str
    treaty_type: TreatyType
    status: TreatyStatus
    proposed_by: str
    proposed_tick: int
    signed_tick: int | None = None
    withdrawn_by: str | None = None
    withdrawn_tick: int | None = None


@dataclass(slots=True)
class MatchAllianceMember:
    player_id: str
    joined_tick: int


@dataclass(slots=True)
class MatchAlliance:
    alliance_id: str
    name: str
    leader_id: str
    formed_tick: int
    members: list[MatchAllianceMember] = field(default_factory=list)


@dataclass(slots=True)
class MatchGroupChatMessage:
    message_id: int
    group_chat_id: str
    sender_id: str
    tick: int
    content: str


@dataclass(slots=True)
class MatchGroupChat:
    group_chat_id: str
    name: str
    member_ids: list[str]
    created_by: str
    created_tick: int
    messages: list[MatchGroupChatMessage] = field(default_factory=list)


class TreatyTransitionError(Exception):
    def __init__(self, *, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class AllianceTransitionError(Exception):
    def __init__(self, *, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class MatchJoinError(Exception):
    def __init__(self, *, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class MatchAccessError(Exception):
    def __init__(self, *, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class GroupChatAccessError(Exception):
    def __init__(self, *, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(slots=True)
class AuthenticatedAgentKeyRecord:
    agent_id: str
    key_hash: str
    is_active: bool = True


@dataclass(slots=True)
class MatchRecord:
    match_id: str
    status: MatchStatus
    tick_interval_seconds: int
    state: MatchState
    map_id: str = "britain"
    max_player_count: int | None = None
    current_player_count: int | None = None
    joinable_player_ids: list[str] = field(default_factory=list)
    agent_profiles: list[AgentProfileResponse] = field(default_factory=list)
    public_competitor_kinds: dict[str, Literal["human", "agent"]] = field(default_factory=dict)
    joined_agents: dict[str, str] = field(default_factory=dict)
    joined_humans: dict[str, str] = field(default_factory=dict)
    order_submissions: list[OrderEnvelope] = field(default_factory=list)
    messages: list[MatchMessage] = field(default_factory=list)
    group_chats: list[MatchGroupChat] = field(default_factory=list)
    treaties: list[MatchTreaty] = field(default_factory=list)
    alliances: list[MatchAlliance] = field(default_factory=list)
    authenticated_agent_keys: list[AuthenticatedAgentKeyRecord] = field(default_factory=list)

    @property
    def public_max_player_count(self) -> int:
        if self.max_player_count is not None:
            return self.max_player_count
        return len(self.state.players)

    @property
    def public_current_player_count(self) -> int:
        if self.current_player_count is not None:
            return self.current_player_count
        if self.joined_agents or self.joined_humans:
            return len(self.joined_agents) + len(self.joined_humans)
        return max(len(self.state.players) - len(self.joinable_player_ids), 0)

    @property
    def public_open_slot_count(self) -> int:
        return max(self.public_max_player_count - self.public_current_player_count, 0)
