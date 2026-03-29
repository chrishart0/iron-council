from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from server.models.api import (
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


class TreatyTransitionError(Exception):
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


class InMemoryMatchRegistry:
    def __init__(self) -> None:
        self._matches: dict[str, MatchRecord] = {}

    def seed_match(self, record: MatchRecord) -> None:
        self._matches[record.match_id] = MatchRecord(
            match_id=record.match_id,
            status=record.status,
            tick_interval_seconds=record.tick_interval_seconds,
            state=record.state.model_copy(deep=True),
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
