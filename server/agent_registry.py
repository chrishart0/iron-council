from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from server import (
    agent_registry_access,
    agent_registry_commands,
    agent_registry_diplomacy,
    agent_registry_messaging,
)
from server.agent_registry_types import (
    AllianceTransitionError,
    AuthenticatedAgentKeyRecord,
    GroupChatAccessError,
    MatchAccessError,
    MatchAlliance,
    MatchAllianceMember,
    MatchGroupChat,
    MatchGroupChatMessage,
    MatchJoinError,
    MatchMessage,
    MatchRecord,
    MatchTreaty,
    TreatyTransitionError,
)
from server.models.api import (
    AgentBriefingMessageBuckets,
    AgentCommandEnvelopeRequest,
    AgentCommandEnvelopeResponse,
    AgentProfileResponse,
    AllianceActionRequest,
    AllianceRecord,
    AuthenticatedAgentContext,
    GroupChatCreateRequest,
    GroupChatMessageCreateRequest,
    GroupChatMessageRecord,
    GroupChatRecord,
    MatchJoinResponse,
    MatchMessageCreateRequest,
    MatchMessageRecord,
    TreatyActionRequest,
    TreatyRecord,
)
from server.models.orders import OrderBatch, OrderEnvelope
from server.models.state import MatchState
from server.registry_seed_data import (
    build_seeded_agent_api_key,
    build_seeded_agent_profiles,
    build_seeded_authenticated_agent_keys,
    build_seeded_match_records,
    build_seeded_profiles_by_key_hash,
)
from server.resolver import TickPhaseEvent

__all__ = [
    "AllianceTransitionError",
    "AuthenticatedAgentKeyRecord",
    "GroupChatAccessError",
    "InMemoryMatchRegistry",
    "MatchAccessError",
    "MatchAlliance",
    "MatchAllianceMember",
    "MatchGroupChat",
    "MatchGroupChatMessage",
    "MatchJoinError",
    "MatchMessage",
    "MatchRecord",
    "MatchTreaty",
    "TreatyTransitionError",
    "AdvancedMatchTick",
    "get_terminal_winner_alliance",
    "is_terminal_victory_tick",
    "build_seeded_agent_api_key",
    "build_seeded_agent_profiles",
    "build_seeded_authenticated_agent_keys",
    "build_seeded_match_records",
    "build_seeded_profiles_by_key_hash",
]


@dataclass(slots=True)
class AdvancedMatchTick:
    match_id: str
    resolved_tick: int
    next_state: MatchState
    accepted_orders: OrderBatch
    events: list[TickPhaseEvent]
    alliances: list[MatchAlliance]


def get_terminal_winner_alliance(advanced_tick: AdvancedMatchTick) -> str | None:
    victory_state = advanced_tick.next_state.victory
    if victory_state.leading_alliance is None:
        return None
    if victory_state.countdown_ticks_remaining != 0:
        return None
    return victory_state.leading_alliance


def is_terminal_victory_tick(advanced_tick: AdvancedMatchTick) -> bool:
    return get_terminal_winner_alliance(advanced_tick) is not None


class InMemoryMatchRegistry:
    def __init__(self) -> None:
        self._matches: dict[str, MatchRecord] = {}
        self._agent_profiles: dict[str, AgentProfileResponse] = {}
        self._authenticated_agents_by_key_hash: dict[str, AuthenticatedAgentContext] = {}
        self._agent_api_key_hashes_by_agent_id: dict[str, set[str]] = {}

    def seed_match(self, record: MatchRecord) -> None:
        cloned_state = record.state.model_copy(deep=True)
        for profile in record.agent_profiles:
            self.seed_agent_profile(profile)
        for authenticated_key in record.authenticated_agent_keys:
            authenticated_profile = self.get_agent_profile(authenticated_key.agent_id)
            if authenticated_profile is None:
                continue
            self.seed_authenticated_agent_key(
                AuthenticatedAgentContext(
                    agent_id=authenticated_profile.agent_id,
                    display_name=authenticated_profile.display_name,
                    is_seeded=authenticated_profile.is_seeded,
                ),
                key_hash=authenticated_key.key_hash,
                is_active=authenticated_key.is_active,
            )
        self._matches[record.match_id] = MatchRecord(
            match_id=record.match_id,
            status=record.status,
            tick_interval_seconds=record.tick_interval_seconds,
            state=cloned_state,
            map_id=record.map_id,
            max_player_count=record.max_player_count,
            current_player_count=record.current_player_count,
            joinable_player_ids=list(record.joinable_player_ids),
            agent_profiles=[],
            public_competitor_kinds=dict(record.public_competitor_kinds),
            joined_agents=dict(record.joined_agents),
            joined_humans=dict(record.joined_humans),
            order_submissions=[
                submission.model_copy(deep=True) for submission in record.order_submissions
            ],
            messages=[
                MatchMessage(
                    message_id=message.message_id,
                    channel=message.channel,
                    sender_id=message.sender_id,
                    recipient_id=message.recipient_id,
                    tick=message.tick,
                    content=message.content,
                )
                for message in record.messages
            ],
            group_chats=[
                MatchGroupChat(
                    group_chat_id=group_chat.group_chat_id,
                    name=group_chat.name,
                    member_ids=list(group_chat.member_ids),
                    created_by=group_chat.created_by,
                    created_tick=group_chat.created_tick,
                    messages=[
                        MatchGroupChatMessage(
                            message_id=message.message_id,
                            group_chat_id=message.group_chat_id,
                            sender_id=message.sender_id,
                            tick=message.tick,
                            content=message.content,
                        )
                        for message in group_chat.messages
                    ],
                )
                for group_chat in record.group_chats
            ],
            treaties=[
                MatchTreaty(
                    treaty_id=treaty.treaty_id,
                    player_a_id=treaty.player_a_id,
                    player_b_id=treaty.player_b_id,
                    treaty_type=treaty.treaty_type,
                    status=treaty.status,
                    proposed_by=treaty.proposed_by,
                    proposed_tick=treaty.proposed_tick,
                    signed_tick=treaty.signed_tick,
                    withdrawn_by=treaty.withdrawn_by,
                    withdrawn_tick=treaty.withdrawn_tick,
                )
                for treaty in record.treaties
            ],
            alliances=(
                [
                    MatchAlliance(
                        alliance_id=alliance.alliance_id,
                        name=alliance.name,
                        leader_id=alliance.leader_id,
                        formed_tick=alliance.formed_tick,
                        members=[
                            MatchAllianceMember(
                                player_id=member.player_id,
                                joined_tick=member.joined_tick,
                            )
                            for member in alliance.members
                        ],
                    )
                    for alliance in record.alliances
                ]
                if record.alliances
                else agent_registry_diplomacy.derive_alliances_from_state(cloned_state)
            ),
            authenticated_agent_keys=[
                AuthenticatedAgentKeyRecord(
                    agent_id=authenticated_key.agent_id,
                    key_hash=authenticated_key.key_hash,
                    is_active=authenticated_key.is_active,
                )
                for authenticated_key in record.authenticated_agent_keys
            ],
        )

    def reset(self) -> None:
        self._matches.clear()
        self._agent_profiles.clear()
        self._authenticated_agents_by_key_hash.clear()
        self._agent_api_key_hashes_by_agent_id.clear()

    def list_matches(self) -> list[MatchRecord]:
        return [self._matches[match_id] for match_id in sorted(self._matches)]

    def get_match(self, match_id: str) -> MatchRecord | None:
        return self._matches.get(match_id)

    def snapshot_match(self, match_id: str) -> MatchRecord:
        return deepcopy(self._matches[match_id])

    def restore_match(self, match_id: str, snapshot: MatchRecord) -> None:
        self._matches[match_id] = deepcopy(snapshot)

    def seed_agent_profile(self, profile: AgentProfileResponse) -> None:
        self._agent_profiles[profile.agent_id] = profile.model_copy(deep=True)

    def get_agent_profile(self, agent_id: str) -> AgentProfileResponse | None:
        profile = self._agent_profiles.get(agent_id)
        if profile is None:
            return None
        return profile.model_copy(deep=True)

    def seed_authenticated_agent_key(
        self,
        agent: AuthenticatedAgentContext,
        *,
        key_hash: str,
        is_active: bool = True,
    ) -> None:
        agent_registry_access.seed_authenticated_agent_key(
            agent=agent,
            key_hash=key_hash,
            is_active=is_active,
            authenticated_agents_by_key_hash=self._authenticated_agents_by_key_hash,
            agent_api_key_hashes_by_agent_id=self._agent_api_key_hashes_by_agent_id,
        )

    def resolve_authenticated_agent(self, api_key: str) -> AuthenticatedAgentContext | None:
        return agent_registry_access.resolve_authenticated_agent(
            api_key=api_key,
            authenticated_agents_by_key_hash=self._authenticated_agents_by_key_hash,
        )

    def deactivate_agent_api_key(self, agent_id: str) -> None:
        agent_registry_access.deactivate_agent_api_key(
            agent_id=agent_id,
            authenticated_agents_by_key_hash=self._authenticated_agents_by_key_hash,
            agent_api_key_hashes_by_agent_id=self._agent_api_key_hashes_by_agent_id,
        )

    def join_match(self, *, match_id: str, agent_id: str) -> MatchJoinResponse:
        return agent_registry_access.join_match(
            record=self._matches[match_id],
            match_id=match_id,
            agent_id=agent_id,
        )

    def require_joined_player_id(self, *, match_id: str, agent_id: str) -> str:
        return agent_registry_access.require_joined_player_id(
            record=self._matches.get(match_id),
            match_id=match_id,
            agent_id=agent_id,
        )

    def require_joined_human_player_id(self, *, match_id: str, user_id: str) -> str:
        return agent_registry_access.require_joined_human_player_id(
            record=self._matches.get(match_id),
            match_id=match_id,
            user_id=user_id,
        )

    def record_submission(self, *, match_id: str, envelope: OrderEnvelope) -> int:
        record = self._matches[match_id]
        record.order_submissions.append(envelope.model_copy(deep=True))
        return len(record.order_submissions) - 1

    def replace_player_submissions(
        self,
        *,
        match_id: str,
        player_id: str,
        tick: int,
        envelope: OrderEnvelope,
    ) -> tuple[int, int]:
        record = self._matches[match_id]
        retained_submissions = [
            submission
            for submission in record.order_submissions
            if submission.player_id != player_id or submission.tick != tick
        ]
        superseded_submission_count = len(record.order_submissions) - len(retained_submissions)
        retained_submissions.append(envelope.model_copy(deep=True))
        record.order_submissions = retained_submissions
        return len(record.order_submissions) - 1, superseded_submission_count

    def advance_match_tick(self, match_id: str) -> AdvancedMatchTick:
        advanced_tick = agent_registry_commands.advance_match_tick(record=self._matches[match_id])
        return AdvancedMatchTick(
            match_id=match_id,
            resolved_tick=advanced_tick.resolved_tick,
            next_state=advanced_tick.next_state,
            accepted_orders=advanced_tick.accepted_orders,
            events=advanced_tick.events,
            alliances=[deepcopy(alliance) for alliance in self._matches[match_id].alliances],
        )

    def apply_command_envelope(
        self,
        *,
        match_id: str,
        command: AgentCommandEnvelopeRequest,
        player_id: str,
    ) -> AgentCommandEnvelopeResponse:
        return agent_registry_commands.apply_command_envelope(
            record=self._matches[match_id],
            match_id=match_id,
            command=command,
            player_id=player_id,
            record_world_message=lambda **kwargs: self._record_world_treaty_message(
                match_id=kwargs["match_id"],
                tick=kwargs["tick"],
                content=kwargs["content"],
            ),
        )

    def list_order_submissions(self, match_id: str) -> list[dict[str, Any]]:
        record = self._matches.get(match_id)
        if record is None:
            return []
        return [submission.model_dump(mode="json") for submission in record.order_submissions]

    def record_message(
        self,
        *,
        match_id: str,
        message: MatchMessageCreateRequest,
        sender_id: str,
    ) -> MatchMessageRecord:
        return agent_registry_messaging.record_message(
            record=self._matches[match_id],
            message=message,
            sender_id=sender_id,
        )

    def create_group_chat(
        self,
        *,
        match_id: str,
        request: GroupChatCreateRequest,
        creator_id: str,
    ) -> GroupChatRecord:
        return agent_registry_messaging.create_group_chat(
            record=self._matches[match_id],
            request=request,
            creator_id=creator_id,
        )

    def list_visible_group_chats(
        self,
        *,
        match_id: str,
        player_id: str,
    ) -> list[GroupChatRecord]:
        return agent_registry_messaging.list_visible_group_chats(
            record=self._matches.get(match_id),
            player_id=player_id,
        )

    def list_group_chat_messages(
        self,
        *,
        match_id: str,
        group_chat_id: str,
        player_id: str,
        since_tick: int | None = None,
    ) -> list[GroupChatMessageRecord]:
        return agent_registry_messaging.list_group_chat_messages(
            record=self._matches[match_id],
            group_chat_id=group_chat_id,
            player_id=player_id,
            since_tick=since_tick,
        )

    def record_group_chat_message(
        self,
        *,
        match_id: str,
        group_chat_id: str,
        message: GroupChatMessageCreateRequest,
        sender_id: str,
    ) -> GroupChatMessageRecord:
        return agent_registry_messaging.record_group_chat_message(
            record=self._matches[match_id],
            group_chat_id=group_chat_id,
            message=message,
            sender_id=sender_id,
        )

    def list_treaties(
        self,
        *,
        match_id: str,
        since_tick: int | None = None,
    ) -> list[TreatyRecord]:
        return agent_registry_diplomacy.list_treaties(
            record=self._matches.get(match_id),
            since_tick=since_tick,
        )

    def list_alliances(self, *, match_id: str) -> list[AllianceRecord]:
        return agent_registry_diplomacy.list_alliances(record=self._matches.get(match_id))

    def apply_alliance_action(
        self,
        *,
        match_id: str,
        action: AllianceActionRequest,
        player_id: str,
    ) -> AllianceRecord | None:
        return agent_registry_diplomacy.apply_alliance_action(
            record=self._matches[match_id],
            match_id=match_id,
            action=action,
            player_id=player_id,
        )

    def apply_treaty_action(
        self,
        *,
        match_id: str,
        action: TreatyActionRequest,
        player_id: str,
    ) -> TreatyRecord:
        return agent_registry_diplomacy.apply_treaty_action(
            record=self._matches[match_id],
            match_id=match_id,
            action=action,
            player_id=player_id,
            record_world_message=self._record_world_treaty_message,
        )

    def list_visible_messages(
        self,
        *,
        match_id: str,
        player_id: str,
    ) -> list[MatchMessageRecord]:
        return agent_registry_messaging.list_visible_messages(
            record=self._matches.get(match_id),
            player_id=player_id,
        )

    def list_briefing_messages(
        self,
        *,
        match_id: str,
        player_id: str,
        since_tick: int | None = None,
    ) -> AgentBriefingMessageBuckets:
        return agent_registry_messaging.list_briefing_messages(
            record=self._matches.get(match_id),
            player_id=player_id,
            since_tick=since_tick,
        )

    def list_visible_group_chat_messages(
        self,
        *,
        match_id: str,
        player_id: str,
        since_tick: int | None = None,
    ) -> list[GroupChatMessageRecord]:
        return agent_registry_messaging.list_visible_group_chat_messages(
            record=self._matches.get(match_id),
            player_id=player_id,
            since_tick=since_tick,
        )

    def _record_world_treaty_message(self, *, match_id: str, tick: int, content: str) -> None:
        agent_registry_messaging.append_message(
            record=self._matches[match_id],
            channel="world",
            sender_id="system",
            recipient_id=None,
            tick=tick,
            content=content,
        )
