from __future__ import annotations

from typing import Protocol

from server.agent_registry_types import (
    AllianceTransitionError,
    MatchAccessError,
    MatchAlliance,
    MatchAllianceMember,
    MatchRecord,
    MatchTreaty,
    TreatyTransitionError,
)
from server.models.api import (
    AgentCommandTreaty,
    AllianceActionRequest,
    AllianceMemberRecord,
    AllianceRecord,
    TreatyActionRequest,
    TreatyRecord,
    TreatyType,
)
from server.models.state import MatchState


class WorldMessageRecorder(Protocol):
    def __call__(self, *, match_id: str, tick: int, content: str) -> None: ...


def list_treaties(
    *,
    record: MatchRecord | None,
    since_tick: int | None = None,
) -> list[TreatyRecord]:
    if record is None:
        return []

    treaties = sorted(
        (
            treaty
            for treaty in record.treaties
            if since_tick is None or treaty_latest_tick(treaty) >= since_tick
        ),
        key=lambda treaty: (
            treaty.player_a_id,
            treaty.player_b_id,
            treaty.treaty_type,
            treaty.treaty_id,
        ),
    )
    return [to_treaty_record(treaty) for treaty in treaties]


def list_alliances(*, record: MatchRecord | None) -> list[AllianceRecord]:
    if record is None:
        return []

    alliances = sorted(
        record.alliances or derive_alliances_from_state(record.state),
        key=lambda alliance: alliance.alliance_id,
    )
    return [to_alliance_record(alliance) for alliance in alliances]


def apply_alliance_action(
    *,
    record: MatchRecord,
    match_id: str,
    action: AllianceActionRequest,
    player_id: str,
) -> AllianceRecord | None:
    player_state = record.state.players[player_id]
    current_alliance_id = player_state.alliance_id

    if action.action == "create":
        if current_alliance_id is not None:
            raise AllianceTransitionError(
                code="player_already_in_alliance",
                message=f"Player '{player_id}' is already in alliance '{current_alliance_id}'.",
            )
        if action.name is None:
            raise AllianceTransitionError(
                code="alliance_name_required",
                message="Alliance creation requires a non-empty name.",
            )

        stored_alliance = MatchAlliance(
            alliance_id=next_alliance_id(record.alliances),
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
        sync_victory_state(record.state)
        return to_alliance_record(stored_alliance)

    if action.action == "join":
        if current_alliance_id is not None:
            raise AllianceTransitionError(
                code="player_already_in_alliance",
                message=f"Player '{player_id}' is already in alliance '{current_alliance_id}'.",
            )
        if action.alliance_id is None:
            raise AllianceTransitionError(
                code="alliance_id_required",
                message="Alliance join requires an alliance_id.",
            )

        join_alliance = find_alliance(alliances=record.alliances, alliance_id=action.alliance_id)
        if join_alliance is None:
            raise AllianceTransitionError(
                code="alliance_not_found",
                message=f"Alliance '{action.alliance_id}' was not found in match '{match_id}'.",
            )

        join_alliance.members.append(
            MatchAllianceMember(
                player_id=player_id,
                joined_tick=record.state.tick,
            )
        )
        player_state.alliance_id = join_alliance.alliance_id
        sync_victory_state(record.state)
        return to_alliance_record(join_alliance)

    if current_alliance_id is None:
        raise AllianceTransitionError(
            code="player_not_in_alliance",
            message=f"Player '{player_id}' is not currently in an alliance.",
        )

    leave_alliance = find_alliance(alliances=record.alliances, alliance_id=current_alliance_id)
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
        sync_victory_state(record.state)
        return None

    if leave_alliance.leader_id == player_id:
        leave_alliance.leader_id = min(member.player_id for member in leave_alliance.members)

    sync_victory_state(record.state)
    return to_alliance_record(leave_alliance)


def apply_treaty_action(
    *,
    record: MatchRecord,
    match_id: str,
    action: TreatyActionRequest,
    player_id: str,
    record_world_message: WorldMessageRecorder,
) -> TreatyRecord:
    player_a_id, player_b_id = sorted((player_id, action.counterparty_id))
    latest_treaty = find_latest_treaty(
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
        return to_treaty_record(stored_treaty)

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
        record_world_message(
            match_id=match_id,
            tick=record.state.tick,
            content=(
                f"Treaty signed: {player_a_id} and {player_b_id} entered a "
                f"{action.treaty_type} treaty."
            ),
        )
        return to_treaty_record(latest_treaty)

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
    record_world_message(
        match_id=match_id,
        tick=record.state.tick,
        content=(
            f"Treaty withdrawn: {player_id} withdrew the {action.treaty_type} "
            f"treaty with {action.counterparty_id}."
        ),
    )
    return to_treaty_record(latest_treaty)


def validate_command_treaty(
    *,
    record: MatchRecord,
    match_id: str,
    treaty: AgentCommandTreaty,
    player_id: str,
) -> None:
    if treaty.counterparty_id not in record.state.players:
        raise MatchAccessError(
            code="player_not_found",
            message=f"Player '{treaty.counterparty_id}' was not found in match '{match_id}'.",
        )
    if player_id == treaty.counterparty_id:
        raise MatchAccessError(
            code="self_targeted_treaty",
            message="Treaty actions require two different players.",
        )


def find_latest_treaty(
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


def treaty_latest_tick(treaty: MatchTreaty) -> int:
    return max(
        treaty.proposed_tick,
        treaty.signed_tick if treaty.signed_tick is not None else treaty.proposed_tick,
        treaty.withdrawn_tick if treaty.withdrawn_tick is not None else treaty.proposed_tick,
    )


def find_alliance(
    *,
    alliances: list[MatchAlliance],
    alliance_id: str,
) -> MatchAlliance | None:
    for alliance in alliances:
        if alliance.alliance_id == alliance_id:
            return alliance
    return None


def next_alliance_id(alliances: list[MatchAlliance]) -> str:
    next_index = 1
    existing_alliance_ids = {alliance.alliance_id for alliance in alliances}
    while f"alliance-{next_index}" in existing_alliance_ids:
        next_index += 1
    return f"alliance-{next_index}"


def to_treaty_record(treaty: MatchTreaty) -> TreatyRecord:
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


def to_alliance_record(alliance: MatchAlliance) -> AllianceRecord:
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


def derive_alliances_from_state(state: MatchState) -> list[MatchAlliance]:
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


def sync_victory_state(state: MatchState) -> None:
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
