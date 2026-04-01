from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from server import agent_registry_diplomacy, agent_registry_messaging
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
from server.auth import hash_api_key
from server.data.maps import load_uk_1900_map
from server.models.api import (
    AgentBriefingMessageBuckets,
    AgentCommandEnvelopeRequest,
    AgentCommandEnvelopeResponse,
    AgentCommandMessage,
    AgentCommandTreaty,
    AgentProfileResponse,
    AllianceActionAcceptanceResponse,
    AllianceActionRequest,
    AllianceRecord,
    AuthenticatedAgentContext,
    GroupChatCreateRequest,
    GroupChatMessageAcceptanceResponse,
    GroupChatMessageCreateRequest,
    GroupChatMessageRecord,
    GroupChatRecord,
    MatchJoinResponse,
    MatchMessageCreateRequest,
    MatchMessageRecord,
    MessageAcceptanceResponse,
    OrderAcceptanceResponse,
    TreatyActionAcceptanceResponse,
    TreatyActionRequest,
    TreatyRecord,
)
from server.models.orders import OrderBatch, OrderEnvelope
from server.models.state import MatchState
from server.order_validation import validate_order_envelope
from server.registry_seed_data import (
    build_seeded_agent_api_key,
    build_seeded_agent_profiles,
    build_seeded_authenticated_agent_keys,
    build_seeded_match_records,
    build_seeded_profiles_by_key_hash,
)
from server.resolver import TickPhaseEvent, resolve_tick

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
                else self._derive_alliances_from_state(cloned_state)
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
        self._agent_api_key_hashes_by_agent_id.setdefault(agent.agent_id, set()).add(key_hash)
        if is_active:
            self._authenticated_agents_by_key_hash[key_hash] = agent.model_copy(deep=True)

    def resolve_authenticated_agent(self, api_key: str) -> AuthenticatedAgentContext | None:
        authenticated_agent = self._authenticated_agents_by_key_hash.get(hash_api_key(api_key))
        if authenticated_agent is None:
            return None
        return authenticated_agent.model_copy(deep=True)

    def deactivate_agent_api_key(self, agent_id: str) -> None:
        for key_hash in self._agent_api_key_hashes_by_agent_id.get(agent_id, set()):
            self._authenticated_agents_by_key_hash.pop(key_hash, None)

    def join_match(self, *, match_id: str, agent_id: str) -> MatchJoinResponse:
        record = self._matches[match_id]
        existing_player_id = record.joined_agents.get(agent_id)
        if existing_player_id is not None:
            return MatchJoinResponse(
                status="accepted",
                match_id=match_id,
                agent_id=agent_id,
                player_id=existing_player_id,
            )

        if not record.joinable_player_ids:
            raise MatchJoinError(
                code="match_not_joinable",
                message=f"Match '{match_id}' does not support agent joins.",
            )

        occupied_player_ids = set(record.joined_agents.values())
        available_player_id = next(
            (
                player_id
                for player_id in record.joinable_player_ids
                if player_id not in occupied_player_ids
            ),
            None,
        )
        if available_player_id is None:
            raise MatchJoinError(
                code="no_open_slots",
                message=f"Match '{match_id}' has no open join slots.",
            )

        record.joined_agents[agent_id] = available_player_id
        return MatchJoinResponse(
            status="accepted",
            match_id=match_id,
            agent_id=agent_id,
            player_id=available_player_id,
        )

    def require_joined_player_id(self, *, match_id: str, agent_id: str) -> str:
        record = self._matches.get(match_id)
        if record is None:
            raise MatchAccessError(
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )

        player_id = record.joined_agents.get(agent_id)
        if player_id is None:
            raise MatchAccessError(
                code="agent_not_joined",
                message=f"Agent '{agent_id}' has not joined match '{match_id}' as a player.",
            )
        return player_id

    def require_joined_human_player_id(self, *, match_id: str, user_id: str) -> str:
        record = self._matches.get(match_id)
        if record is None:
            raise MatchAccessError(
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )

        player_id = record.joined_humans.get(user_id)
        if player_id is None:
            raise MatchAccessError(
                code="human_not_joined",
                message=f"Human user '{user_id}' has not joined match '{match_id}' as a player.",
            )
        return player_id

    def record_submission(self, *, match_id: str, envelope: OrderEnvelope) -> int:
        record = self._matches[match_id]
        record.order_submissions.append(envelope.model_copy(deep=True))
        return len(record.order_submissions) - 1

    def advance_match_tick(self, match_id: str) -> AdvancedMatchTick:
        record = self._matches[match_id]
        current_tick = record.state.tick
        queued_for_current_tick = [
            submission.model_copy(deep=True)
            for submission in record.order_submissions
            if submission.tick == current_tick
        ]
        record.order_submissions = [
            submission for submission in record.order_submissions if submission.tick != current_tick
        ]

        validated_orders = self._validate_queued_orders(
            state=record.state,
            submissions=queued_for_current_tick,
        )
        resolution = resolve_tick(record.state, validated_orders)
        next_state = resolution.next_state.model_copy(update={"tick": current_tick + 1})
        record.state = next_state
        self._sync_victory_state(record.state)
        return AdvancedMatchTick(
            match_id=match_id,
            resolved_tick=record.state.tick,
            next_state=record.state.model_copy(deep=True),
            accepted_orders=validated_orders.model_copy(deep=True),
            events=[event.model_copy(deep=True) for event in resolution.events],
        )

    def apply_command_envelope(
        self,
        *,
        match_id: str,
        command: AgentCommandEnvelopeRequest,
        player_id: str,
    ) -> AgentCommandEnvelopeResponse:
        scratch_registry = self._build_scratch_registry(match_id)
        scratch_registry._apply_command_envelope_mutations(
            match_id=match_id,
            command=command,
            player_id=player_id,
        )
        return self._apply_command_envelope_mutations(
            match_id=match_id,
            command=command,
            player_id=player_id,
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

    def _apply_command_envelope_mutations(
        self,
        *,
        match_id: str,
        command: AgentCommandEnvelopeRequest,
        player_id: str,
    ) -> AgentCommandEnvelopeResponse:
        order_response: OrderAcceptanceResponse | None = None
        message_responses: list[MessageAcceptanceResponse | GroupChatMessageAcceptanceResponse] = []
        treaty_responses: list[TreatyActionAcceptanceResponse] = []
        alliance_response: AllianceActionAcceptanceResponse | None = None

        if self._command_has_orders(command):
            envelope = OrderEnvelope(
                match_id=match_id,
                player_id=player_id,
                tick=command.tick,
                orders=command.orders,
            )
            submission_index = self.record_submission(match_id=match_id, envelope=envelope)
            order_response = OrderAcceptanceResponse(
                status="accepted",
                match_id=match_id,
                player_id=player_id,
                tick=command.tick,
                submission_index=submission_index,
            )

        for message in command.messages:
            self._validate_command_message(match_id=match_id, message=message, player_id=player_id)
            if message.channel == "group":
                accepted_group_message = self.record_group_chat_message(
                    match_id=match_id,
                    group_chat_id=message.group_chat_id or "",
                    message=GroupChatMessageCreateRequest(
                        match_id=match_id,
                        tick=command.tick,
                        content=message.content,
                    ),
                    sender_id=player_id,
                )
                message_responses.append(
                    GroupChatMessageAcceptanceResponse(
                        status="accepted",
                        match_id=match_id,
                        group_chat_id=accepted_group_message.group_chat_id,
                        message=accepted_group_message,
                    )
                )
                continue

            accepted_message = self.record_message(
                match_id=match_id,
                message=MatchMessageCreateRequest(
                    match_id=match_id,
                    tick=command.tick,
                    channel=message.channel,
                    recipient_id=message.recipient_id,
                    content=message.content,
                ),
                sender_id=player_id,
            )
            message_responses.append(
                MessageAcceptanceResponse(
                    status="accepted",
                    match_id=match_id,
                    message_id=accepted_message.message_id,
                    channel=accepted_message.channel,
                    sender_id=accepted_message.sender_id,
                    recipient_id=accepted_message.recipient_id,
                    tick=accepted_message.tick,
                    content=accepted_message.content,
                )
            )

        for treaty in command.treaties:
            self._validate_command_treaty(match_id=match_id, treaty=treaty, player_id=player_id)
            accepted_treaty = self.apply_treaty_action(
                match_id=match_id,
                action=TreatyActionRequest(
                    match_id=match_id,
                    counterparty_id=treaty.counterparty_id,
                    action=treaty.action,
                    treaty_type=treaty.treaty_type,
                ),
                player_id=player_id,
            )
            treaty_responses.append(
                TreatyActionAcceptanceResponse(
                    status="accepted",
                    match_id=match_id,
                    treaty=accepted_treaty,
                )
            )

        if command.alliance is not None:
            accepted_alliance = self.apply_alliance_action(
                match_id=match_id,
                action=AllianceActionRequest(
                    match_id=match_id,
                    action=command.alliance.action,
                    alliance_id=command.alliance.alliance_id,
                    name=command.alliance.name,
                ),
                player_id=player_id,
            )
            alliance_response = AllianceActionAcceptanceResponse(
                status="accepted",
                match_id=match_id,
                player_id=player_id,
                alliance=accepted_alliance,
            )

        return AgentCommandEnvelopeResponse(
            status="accepted",
            match_id=match_id,
            player_id=player_id,
            tick=command.tick,
            orders=order_response,
            messages=message_responses,
            treaties=treaty_responses,
            alliance=alliance_response,
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

    def _build_scratch_registry(self, match_id: str) -> InMemoryMatchRegistry:
        scratch_registry = InMemoryMatchRegistry()
        scratch_registry._matches[match_id] = deepcopy(self._matches[match_id])
        return scratch_registry

    def _command_has_orders(self, command: AgentCommandEnvelopeRequest) -> bool:
        return any(
            (
                command.orders.movements,
                command.orders.recruitment,
                command.orders.upgrades,
                command.orders.transfers,
            )
        )

    def _validate_queued_orders(
        self,
        *,
        state: MatchState,
        submissions: list[OrderEnvelope],
    ) -> OrderBatch:
        aggregated_orders = OrderBatch()
        map_definition = load_uk_1900_map()
        for submission in self._combine_submissions_by_player(submissions):
            validation = validate_order_envelope(submission, state, map_definition)
            aggregated_orders.movements.extend(
                order.model_copy(deep=True) for order in validation.accepted.movements
            )
            aggregated_orders.recruitment.extend(
                order.model_copy(deep=True) for order in validation.accepted.recruitment
            )
            aggregated_orders.upgrades.extend(
                order.model_copy(deep=True) for order in validation.accepted.upgrades
            )
            aggregated_orders.transfers.extend(
                order.model_copy(deep=True) for order in validation.accepted.transfers
            )
        return aggregated_orders

    def _combine_submissions_by_player(
        self,
        submissions: list[OrderEnvelope],
    ) -> list[OrderEnvelope]:
        combined_by_player: dict[str, OrderEnvelope] = {}
        ordered_player_ids: list[str] = []
        for submission in submissions:
            combined_submission = combined_by_player.get(submission.player_id)
            if combined_submission is None:
                combined_by_player[submission.player_id] = submission.model_copy(deep=True)
                ordered_player_ids.append(submission.player_id)
                continue
            combined_submission.orders.movements.extend(
                order.model_copy(deep=True) for order in submission.orders.movements
            )
            combined_submission.orders.recruitment.extend(
                order.model_copy(deep=True) for order in submission.orders.recruitment
            )
            combined_submission.orders.upgrades.extend(
                order.model_copy(deep=True) for order in submission.orders.upgrades
            )
            combined_submission.orders.transfers.extend(
                order.model_copy(deep=True) for order in submission.orders.transfers
            )
        return [combined_by_player[player_id] for player_id in ordered_player_ids]

    def _validate_command_message(
        self,
        *,
        match_id: str,
        message: AgentCommandMessage,
        player_id: str,
    ) -> None:
        agent_registry_messaging.validate_command_message(
            record=self._matches[match_id],
            match_id=match_id,
            message=message,
            player_id=player_id,
        )

    def _validate_command_treaty(
        self,
        *,
        match_id: str,
        treaty: AgentCommandTreaty,
        player_id: str,
    ) -> None:
        agent_registry_diplomacy.validate_command_treaty(
            record=self._matches[match_id],
            match_id=match_id,
            treaty=treaty,
            player_id=player_id,
        )

    def _require_group_chat_member(
        self,
        *,
        match_id: str,
        group_chat_id: str,
        player_id: str,
    ) -> MatchGroupChat:
        return agent_registry_messaging.require_group_chat_member(
            record=self._matches[match_id],
            group_chat_id=group_chat_id,
            player_id=player_id,
        )

    def _derive_alliances_from_state(self, state: MatchState) -> list[MatchAlliance]:
        return agent_registry_diplomacy.derive_alliances_from_state(state)

    def _sync_victory_state(self, state: MatchState) -> None:
        agent_registry_diplomacy.sync_victory_state(state)
