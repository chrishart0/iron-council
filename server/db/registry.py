from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from server.agent_registry import (
    InMemoryMatchRegistry,
    MatchAlliance,
    MatchAllianceMember,
    MatchRecord,
)
from server.db.models import Alliance, Match, Player
from server.models.domain import MatchStatus
from server.models.state import MatchState


def load_match_registry_from_database(database_url: str) -> InMemoryMatchRegistry:
    registry = InMemoryMatchRegistry()
    engine = create_engine(database_url)
    with Session(engine) as session:
        matches = session.scalars(select(Match).order_by(Match.id)).all()
        alliance_rows = session.scalars(
            select(Alliance)
            .where(Alliance.dissolved_tick.is_(None))
            .order_by(Alliance.formed_tick, Alliance.id)
        ).all()
        player_rows = session.scalars(select(Player).order_by(Player.match_id, Player.id)).all()

        alliances_by_match = _load_persisted_alliances_by_match(
            matches=matches,
            alliance_rows=alliance_rows,
            player_rows=player_rows,
        )

        for match in matches:
            match_id = str(match.id)
            persisted_alliances = alliances_by_match.get(match_id, [])
            record = MatchRecord(
                match_id=match_id,
                status=MatchStatus(match.status),
                tick_interval_seconds=int(match.config.get("turn_seconds", 0)),
                state=MatchState.model_validate(match.state),
                alliances=persisted_alliances,
            )
            registry.seed_match(record)

    return registry


def _load_persisted_alliances_by_match(
    *,
    matches: Sequence[Match],
    alliance_rows: Sequence[Alliance],
    player_rows: Sequence[Player],
) -> dict[str, list[MatchAlliance]]:
    players_by_match: dict[str, list[Player]] = defaultdict(list)
    players_by_match_and_alliance: dict[tuple[str, str], list[Player]] = defaultdict(list)
    for player in player_rows:
        players_by_match[str(player.match_id)].append(player)
        if player.alliance_id is None:
            continue
        players_by_match_and_alliance[(str(player.match_id), str(player.alliance_id))].append(
            player
        )

    alliances_by_match: dict[str, list[MatchAlliance]] = {}
    for match in matches:
        match_id = str(match.id)
        state = MatchState.model_validate(match.state)
        derived_registry = InMemoryMatchRegistry()
        derived_alliances = derived_registry._derive_alliances_from_state(state)  # noqa: SLF001
        persisted_player_mapping = _build_persisted_player_mapping(
            canonical_player_ids=sorted(state.players),
            persisted_players=players_by_match.get(match_id, []),
        )
        persisted_rows_for_match = [
            alliance_row for alliance_row in alliance_rows if str(alliance_row.match_id) == match_id
        ]
        persisted_alliances = _merge_persisted_alliance_metadata(
            derived_alliances=derived_alliances,
            persisted_rows=persisted_rows_for_match,
            players_by_match_and_alliance=players_by_match_and_alliance,
            persisted_player_mapping=persisted_player_mapping,
            match_id=match_id,
        )
        if persisted_alliances:
            alliances_by_match[match_id] = persisted_alliances

    return alliances_by_match


def _build_persisted_player_mapping(
    *,
    canonical_player_ids: list[str],
    persisted_players: Sequence[Player],
) -> dict[str, str]:
    sorted_players = sorted(persisted_players, key=lambda player: str(player.id))
    if len(sorted_players) > len(canonical_player_ids):
        return {}

    return {
        str(player.id): canonical_player_ids[index] for index, player in enumerate(sorted_players)
    }


def _merge_persisted_alliance_metadata(
    *,
    derived_alliances: list[MatchAlliance],
    persisted_rows: list[Alliance],
    players_by_match_and_alliance: dict[tuple[str, str], list[Player]],
    persisted_player_mapping: dict[str, str],
    match_id: str,
) -> list[MatchAlliance]:
    if not derived_alliances or len(derived_alliances) != len(persisted_rows):
        return []

    derived_alliances_by_members = {
        frozenset(member.player_id for member in alliance.members): alliance
        for alliance in derived_alliances
    }
    if len(derived_alliances_by_members) != len(derived_alliances):
        return []

    persisted_alliances: list[MatchAlliance] = []
    for persisted_row in persisted_rows:
        persisted_members = sorted(
            players_by_match_and_alliance.get((match_id, str(persisted_row.id)), []),
            key=lambda player: str(player.id),
        )
        canonical_member_ids: list[str] = []
        for player in persisted_members:
            canonical_player_id = persisted_player_mapping.get(str(player.id))
            if canonical_player_id is None:
                return []
            canonical_member_ids.append(canonical_player_id)
        member_key = frozenset(canonical_member_ids)
        derived_alliance = derived_alliances_by_members.get(member_key)
        if derived_alliance is None:
            return []

        canonical_members = sorted(derived_alliance.members, key=lambda member: member.player_id)
        member_joined_ticks = {
            persisted_player_mapping[str(player.id)]: (
                int(player.alliance_joined_tick)
                if player.alliance_joined_tick is not None
                else next(
                    member.joined_tick
                    for member in canonical_members
                    if member.player_id == persisted_player_mapping[str(player.id)]
                )
            )
            for player in persisted_members
        }
        leader_id = persisted_player_mapping.get(str(persisted_row.leader_id))
        if leader_id is None or leader_id not in member_key:
            return []

        persisted_alliances.append(
            MatchAlliance(
                alliance_id=derived_alliance.alliance_id,
                name=persisted_row.name,
                leader_id=leader_id,
                formed_tick=int(persisted_row.formed_tick),
                members=[
                    MatchAllianceMember(
                        player_id=member.player_id,
                        joined_tick=member_joined_ticks.get(member.player_id, member.joined_tick),
                    )
                    for member in canonical_members
                ],
            )
        )
        del derived_alliances_by_members[member_key]

    if derived_alliances_by_members:
        return []

    return sorted(persisted_alliances, key=lambda alliance: alliance.alliance_id)
