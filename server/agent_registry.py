from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from server.models.api import (
    AllianceActionRequest,
    AllianceMemberRecord,
    AllianceRecord,
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


@dataclass(slots=True)
class MatchRecord:
    match_id: str
    status: MatchStatus
    tick_interval_seconds: int
    state: MatchState
    order_submissions: list[OrderEnvelope] = field(default_factory=list)
    messages: list[MatchMessage] = field(default_factory=list)
    treaties: list[MatchTreaty] = field(default_factory=list)
    alliances: list[MatchAlliance] = field(default_factory=list)


class InMemoryMatchRegistry:
    def __init__(self) -> None:
        self._matches: dict[str, MatchRecord] = {}

    def seed_match(self, record: MatchRecord) -> None:
        cloned_state = record.state.model_copy(deep=True)
        self._matches[record.match_id] = MatchRecord(
            match_id=record.match_id,
            status=record.status,
            tick_interval_seconds=record.tick_interval_seconds,
            state=cloned_state,
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
        )

    def reset(self) -> None:
        self._matches.clear()

    def list_matches(self) -> list[MatchRecord]:
        return [self._matches[match_id] for match_id in sorted(self._matches)]

    def get_match(self, match_id: str) -> MatchRecord | None:
        return self._matches.get(match_id)

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
    ) -> MatchMessageRecord:
        stored_message = self._append_message(
            match_id=match_id,
            channel=message.channel,
            sender_id=message.sender_id,
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
    ) -> AllianceRecord | None:
        record = self._matches[match_id]
        player_state = record.state.players[action.player_id]
        current_alliance_id = player_state.alliance_id

        if action.action == "create":
            if current_alliance_id is not None:
                raise AllianceTransitionError(
                    code="player_already_in_alliance",
                    message=(
                        f"Player '{action.player_id}' is already in alliance "
                        f"'{current_alliance_id}'."
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
                leader_id=action.player_id,
                formed_tick=record.state.tick,
                members=[
                    MatchAllianceMember(
                        player_id=action.player_id,
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
                        f"Player '{action.player_id}' is already in alliance "
                        f"'{current_alliance_id}'."
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
                    player_id=action.player_id,
                    joined_tick=record.state.tick,
                )
            )
            player_state.alliance_id = join_alliance.alliance_id
            self._sync_victory_state(record.state)
            return self._to_alliance_record(join_alliance)

        if current_alliance_id is None:
            raise AllianceTransitionError(
                code="player_not_in_alliance",
                message=f"Player '{action.player_id}' is not currently in an alliance.",
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
            member for member in leave_alliance.members if member.player_id != action.player_id
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

        if leave_alliance.leader_id == action.player_id:
            leave_alliance.leader_id = min(member.player_id for member in leave_alliance.members)

        self._sync_victory_state(record.state)
        return self._to_alliance_record(leave_alliance)

    def apply_treaty_action(
        self,
        *,
        match_id: str,
        action: TreatyActionRequest,
    ) -> TreatyRecord:
        record = self._matches[match_id]
        player_a_id, player_b_id = sorted((action.player_id, action.counterparty_id))
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
                proposed_by=action.player_id,
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
            if latest_treaty.status != "proposed" or latest_treaty.proposed_by == action.player_id:
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
        latest_treaty.withdrawn_by = action.player_id
        latest_treaty.withdrawn_tick = record.state.tick
        self._record_world_treaty_message(
            match_id=match_id,
            tick=record.state.tick,
            content=(
                f"Treaty withdrawn: {action.player_id} withdrew the {action.treaty_type} "
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
    return [
        MatchRecord(
            match_id=primary_match_id,
            status=MatchStatus.ACTIVE,
            tick_interval_seconds=30,
            state=MatchState.model_validate(_seeded_match_state_payload()),
        ),
        MatchRecord(
            match_id=secondary_match_id,
            status=MatchStatus.PAUSED,
            tick_interval_seconds=45,
            state=MatchState.model_validate(
                {
                    **_seeded_match_state_payload(),
                    "tick": 7,
                }
            ),
        ),
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
