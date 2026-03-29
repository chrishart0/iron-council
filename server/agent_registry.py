from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from server.auth import hash_api_key
from server.models.api import (
    AgentProfileHistory,
    AgentProfileRating,
    AgentProfileResponse,
    AllianceActionRequest,
    AllianceMemberRecord,
    AllianceRecord,
    AuthenticatedAgentContext,
    MatchJoinResponse,
    MatchMessageCreateRequest,
    MatchMessageRecord,
    MessageChannel,
    TreatyActionRequest,
    TreatyRecord,
    TreatyStatus,
    TreatyType,
)
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


@dataclass(slots=True)
class MatchRecord:
    match_id: str
    status: MatchStatus
    tick_interval_seconds: int
    state: MatchState
    joinable_player_ids: list[str] = field(default_factory=list)
    agent_profiles: list[AgentProfileResponse] = field(default_factory=list)
    joined_agents: dict[str, str] = field(default_factory=dict)
    order_submissions: list[OrderEnvelope] = field(default_factory=list)
    messages: list[MatchMessage] = field(default_factory=list)
    treaties: list[MatchTreaty] = field(default_factory=list)
    alliances: list[MatchAlliance] = field(default_factory=list)
    authenticated_agent_keys: list[AuthenticatedAgentKeyRecord] = field(default_factory=list)


@dataclass(slots=True)
class AuthenticatedAgentKeyRecord:
    agent_id: str
    key_hash: str
    is_active: bool = True


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
            joinable_player_ids=list(record.joinable_player_ids),
            agent_profiles=[],
            joined_agents=dict(record.joined_agents),
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

    def record_submission(self, *, match_id: str, envelope: OrderEnvelope) -> int:
        record = self._matches[match_id]
        record.order_submissions.append(envelope.model_copy(deep=True))
        return len(record.order_submissions) - 1

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
        stored_message = self._append_message(
            match_id=match_id,
            channel=message.channel,
            sender_id=sender_id,
            recipient_id=message.recipient_id,
            tick=message.tick,
            content=message.content,
        )
        return MatchMessageRecord(
            message_id=stored_message.message_id,
            channel=stored_message.channel,
            sender_id=stored_message.sender_id,
            recipient_id=stored_message.recipient_id,
            tick=stored_message.tick,
            content=stored_message.content,
        )

    def list_treaties(self, *, match_id: str) -> list[TreatyRecord]:
        record = self._matches.get(match_id)
        if record is None:
            return []

        treaties = sorted(
            record.treaties,
            key=lambda treaty: (
                treaty.player_a_id,
                treaty.player_b_id,
                treaty.treaty_type,
                treaty.treaty_id,
            ),
        )
        return [self._to_treaty_record(treaty) for treaty in treaties]

    def list_alliances(self, *, match_id: str) -> list[AllianceRecord]:
        record = self._matches.get(match_id)
        if record is None:
            return []

        alliances = sorted(record.alliances, key=lambda alliance: alliance.alliance_id)
        return [self._to_alliance_record(alliance) for alliance in alliances]

    def apply_alliance_action(
        self,
        *,
        match_id: str,
        action: AllianceActionRequest,
        player_id: str,
    ) -> AllianceRecord | None:
        record = self._matches[match_id]

        player_state = record.state.players[player_id]
        current_alliance_id = player_state.alliance_id

        if action.action == "create":
            if current_alliance_id is not None:
                raise AllianceTransitionError(
                    code="player_already_in_alliance",
                    message=(
                        f"Player '{player_id}' is already in alliance '{current_alliance_id}'."
                    ),
                )
            if action.name is None:
                raise AllianceTransitionError(
                    code="alliance_name_required",
                    message="Alliance creation requires a non-empty name.",
                )

            stored_alliance = MatchAlliance(
                alliance_id=self._next_alliance_id(record.alliances),
                name=action.name,
                leader_id=player_id,
                formed_tick=record.state.tick,
                members=[
                    MatchAllianceMember(
                        player_id=player_id,
                        joined_tick=record.state.tick,
                    )
                ],
            )
            record.alliances.append(stored_alliance)
            player_state.alliance_id = stored_alliance.alliance_id
            self._sync_victory_state(record.state)
            return self._to_alliance_record(stored_alliance)

        if action.action == "join":
            if current_alliance_id is not None:
                raise AllianceTransitionError(
                    code="player_already_in_alliance",
                    message=(
                        f"Player '{player_id}' is already in alliance '{current_alliance_id}'."
                    ),
                )
            if action.alliance_id is None:
                raise AllianceTransitionError(
                    code="alliance_id_required",
                    message="Alliance join requires an alliance_id.",
                )

            join_alliance = self._find_alliance(
                alliances=record.alliances,
                alliance_id=action.alliance_id,
            )
            if join_alliance is None:
                raise AllianceTransitionError(
                    code="alliance_not_found",
                    message=(
                        f"Alliance '{action.alliance_id}' was not found in match '{match_id}'."
                    ),
                )

            join_alliance.members.append(
                MatchAllianceMember(
                    player_id=player_id,
                    joined_tick=record.state.tick,
                )
            )
            player_state.alliance_id = join_alliance.alliance_id
            self._sync_victory_state(record.state)
            return self._to_alliance_record(join_alliance)

        if current_alliance_id is None:
            raise AllianceTransitionError(
                code="player_not_in_alliance",
                message=f"Player '{player_id}' is not currently in an alliance.",
            )

        leave_alliance = self._find_alliance(
            alliances=record.alliances,
            alliance_id=current_alliance_id,
        )
        if leave_alliance is None:
            raise AllianceTransitionError(
                code="alliance_not_found",
                message=f"Alliance '{current_alliance_id}' was not found in match '{match_id}'.",
            )

        leave_alliance.members = [
            member for member in leave_alliance.members if member.player_id != player_id
        ]
        player_state.alliance_id = None

        if not leave_alliance.members:
            record.alliances = [
                alliance
                for alliance in record.alliances
                if alliance.alliance_id != leave_alliance.alliance_id
            ]
            self._sync_victory_state(record.state)
            return None

        if leave_alliance.leader_id == player_id:
            leave_alliance.leader_id = min(member.player_id for member in leave_alliance.members)

        self._sync_victory_state(record.state)
        return self._to_alliance_record(leave_alliance)

    def apply_treaty_action(
        self,
        *,
        match_id: str,
        action: TreatyActionRequest,
        player_id: str,
    ) -> TreatyRecord:
        record = self._matches[match_id]

        player_a_id, player_b_id = sorted((player_id, action.counterparty_id))
        latest_treaty = self._find_latest_treaty(
            treaties=record.treaties,
            player_a_id=player_a_id,
            player_b_id=player_b_id,
            treaty_type=action.treaty_type,
        )

        if action.action == "propose":
            if latest_treaty is not None and latest_treaty.status != "withdrawn":
                raise TreatyTransitionError(
                    code="unsupported_treaty_transition",
                    message=(
                        f"Cannot propose treaty '{action.treaty_type}' for players "
                        f"'{player_a_id}' and '{player_b_id}'."
                    ),
                )
            stored_treaty = MatchTreaty(
                treaty_id=len(record.treaties),
                player_a_id=player_a_id,
                player_b_id=player_b_id,
                treaty_type=action.treaty_type,
                status="proposed",
                proposed_by=player_id,
                proposed_tick=record.state.tick,
            )
            record.treaties.append(stored_treaty)
            return self._to_treaty_record(stored_treaty)

        if latest_treaty is None and action.action == "accept":
            raise TreatyTransitionError(
                code="unsupported_treaty_transition",
                message=(
                    f"Cannot accept treaty '{action.treaty_type}' for players "
                    f"'{player_a_id}' and '{player_b_id}'."
                ),
            )

        if latest_treaty is None:
            raise TreatyTransitionError(
                code="treaty_not_found",
                message=(
                    f"No treaty exists for players '{player_a_id}' and '{player_b_id}' "
                    f"with type '{action.treaty_type}'."
                ),
            )

        if action.action == "accept":
            if latest_treaty.status != "proposed" or latest_treaty.proposed_by == player_id:
                raise TreatyTransitionError(
                    code="unsupported_treaty_transition",
                    message=(
                        f"Cannot accept treaty '{action.treaty_type}' for players "
                        f"'{player_a_id}' and '{player_b_id}'."
                    ),
                )
            latest_treaty.status = "active"
            latest_treaty.signed_tick = record.state.tick
            self._record_world_treaty_message(
                match_id=match_id,
                tick=record.state.tick,
                content=(
                    f"Treaty signed: {player_a_id} and {player_b_id} entered a "
                    f"{action.treaty_type} treaty."
                ),
            )
            return self._to_treaty_record(latest_treaty)

        if latest_treaty.status not in {"proposed", "active"}:
            raise TreatyTransitionError(
                code="unsupported_treaty_transition",
                message=(
                    f"Cannot withdraw treaty '{action.treaty_type}' for players "
                    f"'{player_a_id}' and '{player_b_id}'."
                ),
            )
        latest_treaty.status = "withdrawn"
        latest_treaty.withdrawn_by = player_id
        latest_treaty.withdrawn_tick = record.state.tick
        self._record_world_treaty_message(
            match_id=match_id,
            tick=record.state.tick,
            content=(
                f"Treaty withdrawn: {player_id} withdrew the {action.treaty_type} "
                f"treaty with {action.counterparty_id}."
            ),
        )
        return self._to_treaty_record(latest_treaty)

    def list_visible_messages(self, *, match_id: str, player_id: str) -> list[MatchMessageRecord]:
        record = self._matches.get(match_id)
        if record is None:
            return []

        visible_messages: list[MatchMessageRecord] = []
        for message in record.messages:
            is_visible_direct_message = message.channel == "direct" and (
                message.sender_id == player_id or message.recipient_id == player_id
            )
            if message.channel == "world" or is_visible_direct_message:
                visible_messages.append(
                    MatchMessageRecord(
                        message_id=message.message_id,
                        channel=message.channel,
                        sender_id=message.sender_id,
                        recipient_id=message.recipient_id,
                        tick=message.tick,
                        content=message.content,
                    )
                )
        return visible_messages

    def _append_message(
        self,
        *,
        match_id: str,
        channel: MessageChannel,
        sender_id: str,
        recipient_id: str | None,
        tick: int,
        content: str,
    ) -> MatchMessage:
        record = self._matches[match_id]
        stored_message = MatchMessage(
            message_id=len(record.messages),
            channel=channel,
            sender_id=sender_id,
            recipient_id=recipient_id,
            tick=tick,
            content=content,
        )
        record.messages.append(stored_message)
        return stored_message

    def _record_world_treaty_message(self, *, match_id: str, tick: int, content: str) -> None:
        self._append_message(
            match_id=match_id,
            channel="world",
            sender_id="system",
            recipient_id=None,
            tick=tick,
            content=content,
        )

    def _find_latest_treaty(
        self,
        *,
        treaties: list[MatchTreaty],
        player_a_id: str,
        player_b_id: str,
        treaty_type: TreatyType,
    ) -> MatchTreaty | None:
        for treaty in reversed(treaties):
            if (
                treaty.player_a_id == player_a_id
                and treaty.player_b_id == player_b_id
                and treaty.treaty_type == treaty_type
            ):
                return treaty
        return None

    def _find_alliance(
        self,
        *,
        alliances: list[MatchAlliance],
        alliance_id: str,
    ) -> MatchAlliance | None:
        for alliance in alliances:
            if alliance.alliance_id == alliance_id:
                return alliance
        return None

    def _next_alliance_id(self, alliances: list[MatchAlliance]) -> str:
        next_index = 1
        existing_alliance_ids = {alliance.alliance_id for alliance in alliances}
        while f"alliance-{next_index}" in existing_alliance_ids:
            next_index += 1
        return f"alliance-{next_index}"

    def _to_treaty_record(self, treaty: MatchTreaty) -> TreatyRecord:
        return TreatyRecord(
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

    def _to_alliance_record(self, alliance: MatchAlliance) -> AllianceRecord:
        return AllianceRecord(
            alliance_id=alliance.alliance_id,
            name=alliance.name,
            leader_id=alliance.leader_id,
            formed_tick=alliance.formed_tick,
            members=[
                AllianceMemberRecord(
                    player_id=member.player_id,
                    joined_tick=member.joined_tick,
                )
                for member in sorted(alliance.members, key=lambda member: member.player_id)
            ],
        )

    def _derive_alliances_from_state(self, state: MatchState) -> list[MatchAlliance]:
        memberships: dict[str, list[str]] = {}
        for player_id, player_state in state.players.items():
            if player_state.alliance_id is None:
                continue
            memberships.setdefault(player_state.alliance_id, []).append(player_id)

        alliances: list[MatchAlliance] = []
        for alliance_id in sorted(memberships):
            member_ids = sorted(memberships[alliance_id])
            leader_id = member_ids[0]
            alliances.append(
                MatchAlliance(
                    alliance_id=alliance_id,
                    name=alliance_id,
                    leader_id=leader_id,
                    formed_tick=state.tick,
                    members=[
                        MatchAllianceMember(player_id=member_id, joined_tick=state.tick)
                        for member_id in member_ids
                    ],
                )
            )
        return alliances

    def _sync_victory_state(self, state: MatchState) -> None:
        coalition_city_counts: dict[str, int] = {}
        for city_state in state.cities.values():
            if city_state.owner is None:
                continue

            player_state = state.players.get(city_state.owner)
            if player_state is None:
                continue

            coalition_id = player_state.alliance_id or city_state.owner
            coalition_city_counts[coalition_id] = coalition_city_counts.get(coalition_id, 0) + 1

        if coalition_city_counts:
            cities_held = max(coalition_city_counts.values())
            leaders = [
                coalition_id
                for coalition_id, city_count in coalition_city_counts.items()
                if city_count == cities_held
            ]
            leading_alliance = leaders[0] if len(leaders) == 1 else None
        else:
            cities_held = 0
            leading_alliance = None

        previous_leader = state.victory.leading_alliance
        if leading_alliance is None or cities_held < state.victory.threshold:
            countdown_ticks_remaining = None
        elif previous_leader is None:
            countdown_ticks_remaining = state.victory.threshold
        elif previous_leader != leading_alliance:
            countdown_ticks_remaining = None
        elif state.victory.countdown_ticks_remaining is None:
            countdown_ticks_remaining = state.victory.threshold
        else:
            countdown_ticks_remaining = state.victory.countdown_ticks_remaining

        state.victory.leading_alliance = leading_alliance
        state.victory.cities_held = cities_held
        state.victory.countdown_ticks_remaining = countdown_ticks_remaining


def build_seeded_match_records(
    *,
    primary_match_id: str = "match-alpha",
    secondary_match_id: str = "match-beta",
) -> list[MatchRecord]:
    seeded_profiles = build_seeded_agent_profiles()
    seeded_authenticated_keys = build_seeded_authenticated_agent_keys()
    return [
        MatchRecord(
            match_id=primary_match_id,
            status=MatchStatus.ACTIVE,
            tick_interval_seconds=30,
            state=MatchState.model_validate(_seeded_match_state_payload()),
            agent_profiles=seeded_profiles,
            joined_agents={
                f"agent-{player_id}": player_id
                for player_id in _seeded_match_state_payload()["players"]
            },
            authenticated_agent_keys=seeded_authenticated_keys,
        ),
        MatchRecord(
            match_id=secondary_match_id,
            status=MatchStatus.PAUSED,
            tick_interval_seconds=45,
            joinable_player_ids=sorted(_seeded_match_state_payload()["players"]),
            state=MatchState.model_validate(
                {
                    **_seeded_match_state_payload(),
                    "tick": 7,
                }
            ),
            agent_profiles=seeded_profiles,
            authenticated_agent_keys=seeded_authenticated_keys,
        ),
    ]


def build_seeded_agent_profiles() -> list[AgentProfileResponse]:
    seeded_profile_specs = (
        ("player-1", "Arthur", 1210),
        ("player-2", "Morgana", 1190),
        ("player-3", "Gawain", 1175),
        ("player-4", "Lancelot", 1160),
        ("player-5", "Percival", 1140),
    )
    return [
        AgentProfileResponse(
            agent_id=f"agent-{player_id}",
            display_name=display_name,
            is_seeded=True,
            rating=AgentProfileRating(elo=elo_rating, provisional=True),
            history=AgentProfileHistory(
                matches_played=0,
                wins=0,
                losses=0,
                draws=0,
            ),
        )
        for player_id, display_name, elo_rating in seeded_profile_specs
    ]


def build_seeded_agent_api_key(agent_id: str) -> str:
    return f"seed-api-key-for-{agent_id}"


def build_seeded_authenticated_agent_keys() -> list[AuthenticatedAgentKeyRecord]:
    return [
        AuthenticatedAgentKeyRecord(
            agent_id=profile.agent_id,
            key_hash=hash_api_key(build_seeded_agent_api_key(profile.agent_id)),
            is_active=True,
        )
        for profile in build_seeded_agent_profiles()
    ]


def _seeded_match_state_payload() -> dict[str, Any]:
    return {
        "tick": 142,
        "cities": {
            "london": {
                "owner": "player-1",
                "population": 12,
                "resources": {"food": 3, "production": 2, "money": 8},
                "upgrades": {"economy": 2, "military": 1, "fortification": 0},
                "garrison": 15,
                "building_queue": [{"type": "fortification", "tier": 1, "ticks_remaining": 3}],
            },
            "manchester": {
                "owner": "player-2",
                "population": 10,
                "resources": {"food": 2, "production": 4, "money": 1},
                "upgrades": {"economy": 0, "military": 1, "fortification": 0},
                "garrison": 9,
                "building_queue": [],
            },
            "birmingham": {
                "owner": "player-3",
                "population": 8,
                "resources": {"food": 1, "production": 5, "money": 1},
                "upgrades": {"economy": 0, "military": 0, "fortification": 1},
                "garrison": 7,
                "building_queue": [],
            },
            "leeds": {
                "owner": "player-4",
                "population": 7,
                "resources": {"food": 1, "production": 3, "money": 1},
                "upgrades": {"economy": 1, "military": 0, "fortification": 0},
                "garrison": 11,
                "building_queue": [],
            },
            "inverness": {
                "owner": "player-5",
                "population": 5,
                "resources": {"food": 3, "production": 1, "money": 0},
                "upgrades": {"economy": 0, "military": 2, "fortification": 0},
                "garrison": 13,
                "building_queue": [],
            },
        },
        "armies": [
            {
                "id": "army-c",
                "owner": "player-3",
                "troops": 18,
                "location": None,
                "destination": "birmingham",
                "path": ["birmingham"],
                "ticks_remaining": 2,
            },
            {
                "id": "army-a",
                "owner": "player-2",
                "troops": 14,
                "location": None,
                "destination": "leeds",
                "path": ["leeds"],
                "ticks_remaining": 1,
            },
            {
                "id": "army-b",
                "owner": "player-1",
                "troops": 20,
                "location": "london",
                "destination": None,
                "path": None,
                "ticks_remaining": 0,
            },
            {
                "id": "army-z",
                "owner": "player-5",
                "troops": 25,
                "location": None,
                "destination": "inverness",
                "path": ["inverness"],
                "ticks_remaining": 3,
            },
        ],
        "players": {
            "player-1": {
                "resources": {"food": 120, "production": 85, "money": 200},
                "cities_owned": ["london"],
                "alliance_id": "alliance-red",
                "is_eliminated": False,
            },
            "player-2": {
                "resources": {"food": 90, "production": 70, "money": 110},
                "cities_owned": ["manchester"],
                "alliance_id": "alliance-red",
                "is_eliminated": False,
            },
            "player-3": {
                "resources": {"food": 75, "production": 65, "money": 80},
                "cities_owned": ["birmingham"],
                "alliance_id": None,
                "is_eliminated": False,
            },
            "player-4": {
                "resources": {"food": 60, "production": 55, "money": 70},
                "cities_owned": ["leeds"],
                "alliance_id": None,
                "is_eliminated": False,
            },
            "player-5": {
                "resources": {"food": 40, "production": 35, "money": 30},
                "cities_owned": ["inverness"],
                "alliance_id": None,
                "is_eliminated": False,
            },
        },
        "victory": {
            "leading_alliance": "alliance-red",
            "cities_held": 2,
            "threshold": 13,
            "countdown_ticks_remaining": None,
        },
    }
