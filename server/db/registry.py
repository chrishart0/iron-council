from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from server.agent_registry import (
    AdvancedMatchTick,
    AuthenticatedAgentKeyRecord,
    InMemoryMatchRegistry,
    MatchAlliance,
    MatchAllianceMember,
    MatchRecord,
    build_seeded_agent_profiles,
)
from server.db.models import Alliance, ApiKey, Match, Player, TickLog
from server.models.api import (
    AgentProfileHistory,
    AgentProfileRating,
    AgentProfileResponse,
    MatchHistoryEntry,
    MatchHistoryResponse,
    MatchReplayTickResponse,
)
from server.models.domain import MatchStatus
from server.models.state import MatchState


class MatchHistoryNotFoundError(KeyError):
    pass


class TickHistoryNotFoundError(KeyError):
    pass


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
        api_key_rows = session.scalars(select(ApiKey).order_by(ApiKey.id)).all()

        alliances_by_match = _load_persisted_alliances_by_match(
            matches=matches,
            alliance_rows=alliance_rows,
            player_rows=player_rows,
        )
        agent_profiles_by_match = _load_agent_profiles_by_match(
            matches=matches,
            player_rows=player_rows,
        )
        authenticated_keys_by_match = _load_authenticated_agent_keys_by_match(
            matches=matches,
            player_rows=player_rows,
            api_key_rows=api_key_rows,
        )
        joined_agents_by_match = _load_joined_agents_by_match(
            matches=matches,
            player_rows=player_rows,
        )

        for match in matches:
            match_id = str(match.id)
            persisted_alliances = alliances_by_match.get(match_id, [])
            state = MatchState.model_validate(match.state)
            record = MatchRecord(
                match_id=match_id,
                status=MatchStatus(match.status),
                tick_interval_seconds=int(match.config.get("turn_seconds", 0)),
                state=state,
                joinable_player_ids=(
                    sorted(state.players) if match.status == MatchStatus.PAUSED.value else []
                ),
                agent_profiles=agent_profiles_by_match.get(match_id, build_seeded_agent_profiles()),
                joined_agents=joined_agents_by_match.get(match_id, {}),
                alliances=persisted_alliances,
                authenticated_agent_keys=authenticated_keys_by_match.get(match_id, []),
            )
            registry.seed_match(record)

    return registry


def persist_advanced_match_tick(*, database_url: str, advanced_tick: AdvancedMatchTick) -> None:
    engine = create_engine(database_url)
    with Session(engine) as session, session.begin():
        match = session.get(Match, advanced_tick.match_id)
        if match is None:
            raise KeyError(f"Match '{advanced_tick.match_id}' was not found.")

        match.current_tick = advanced_tick.resolved_tick
        match.state = advanced_tick.next_state.model_dump(mode="json")
        session.add(
            TickLog(
                match_id=advanced_tick.match_id,
                tick=advanced_tick.resolved_tick,
                state_snapshot=advanced_tick.next_state.model_dump(mode="json"),
                orders=advanced_tick.accepted_orders.model_dump(mode="json"),
                events=[event.model_dump(mode="json") for event in advanced_tick.events],
            )
        )


def get_match_history(*, database_url: str, match_id: str) -> MatchHistoryResponse:
    engine = create_engine(database_url)
    with Session(engine) as session:
        match = session.get(Match, match_id)
        if match is None:
            raise MatchHistoryNotFoundError(match_id)

        ticks = (
            session.execute(
                select(TickLog.tick)
                .where(TickLog.match_id == match_id)
                .order_by(TickLog.tick, TickLog.id)
            )
            .scalars()
            .all()
        )

    return MatchHistoryResponse(
        match_id=str(match.id),
        status=MatchStatus(match.status),
        current_tick=int(match.current_tick),
        tick_interval_seconds=int(match.config.get("turn_seconds", 0)),
        history=[MatchHistoryEntry(tick=int(tick)) for tick in ticks],
    )


def get_match_replay_tick(
    *, database_url: str, match_id: str, tick: int
) -> MatchReplayTickResponse:
    engine = create_engine(database_url)
    with Session(engine) as session:
        match = session.get(Match, match_id)
        if match is None:
            raise MatchHistoryNotFoundError(match_id)

        tick_row = session.scalar(
            select(TickLog)
            .where(TickLog.match_id == match_id, TickLog.tick == tick)
            .order_by(TickLog.id)
        )
        if tick_row is None:
            raise TickHistoryNotFoundError((match_id, tick))

    return MatchReplayTickResponse(
        match_id=str(match.id),
        tick=int(tick_row.tick),
        state_snapshot=tick_row.state_snapshot,
        orders=tick_row.orders,
        events=tick_row.events,
    )


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


def _load_agent_profiles_by_match(
    *,
    matches: Sequence[Match],
    player_rows: Sequence[Player],
) -> dict[str, list[AgentProfileResponse]]:
    players_by_match: dict[str, list[Player]] = defaultdict(list)
    persisted_agent_ids: set[str] = set()
    for player in player_rows:
        players_by_match[str(player.match_id)].append(player)

    for match in matches:
        state = MatchState.model_validate(match.state)
        persisted_player_mapping = _build_persisted_player_mapping(
            canonical_player_ids=sorted(state.players),
            persisted_players=players_by_match.get(str(match.id), []),
        )
        for player in players_by_match.get(str(match.id), []):
            if not player.is_agent:
                continue
            canonical_player_id = persisted_player_mapping.get(str(player.id))
            if canonical_player_id is not None:
                persisted_agent_ids.add(f"agent-{canonical_player_id}")

    fallback_profiles_by_agent_id = {
        profile.agent_id: profile
        for profile in build_seeded_agent_profiles()
        if profile.agent_id in persisted_agent_ids
    }
    profiles_by_match: dict[str, list[AgentProfileResponse]] = {}
    for match in matches:
        match_id = str(match.id)
        state = MatchState.model_validate(match.state)
        persisted_player_mapping = _build_persisted_player_mapping(
            canonical_player_ids=sorted(state.players),
            persisted_players=players_by_match.get(match_id, []),
        )
        loaded_profiles = [
            AgentProfileResponse(
                agent_id=f"agent-{canonical_player_id}",
                display_name=player.display_name,
                is_seeded=True,
                rating=AgentProfileRating(elo=int(player.elo_rating), provisional=True),
                history=AgentProfileHistory(
                    matches_played=0,
                    wins=0,
                    losses=0,
                    draws=0,
                ),
            )
            for player in sorted(
                players_by_match.get(match_id, []),
                key=lambda persisted: str(persisted.id),
            )
            if player.is_agent
            and (canonical_player_id := persisted_player_mapping.get(str(player.id))) is not None
        ]
        merged_profiles = {
            profile.agent_id: profile for profile in fallback_profiles_by_agent_id.values()
        }
        for profile in loaded_profiles:
            merged_profiles[profile.agent_id] = profile
        profiles_by_match[match_id] = [
            merged_profiles[agent_id] for agent_id in sorted(merged_profiles)
        ]

    return profiles_by_match


def _load_authenticated_agent_keys_by_match(
    *,
    matches: Sequence[Match],
    player_rows: Sequence[Player],
    api_key_rows: Sequence[ApiKey],
) -> dict[str, list[AuthenticatedAgentKeyRecord]]:
    players_by_match: dict[str, list[Player]] = defaultdict(list)
    api_keys_by_id = {str(api_key.id): api_key for api_key in api_key_rows}
    for player in player_rows:
        players_by_match[str(player.match_id)].append(player)

    authenticated_keys_by_match: dict[str, list[AuthenticatedAgentKeyRecord]] = {}
    for match in matches:
        match_id = str(match.id)
        state = MatchState.model_validate(match.state)
        persisted_player_mapping = _build_persisted_player_mapping(
            canonical_player_ids=sorted(state.players),
            persisted_players=players_by_match.get(match_id, []),
        )
        authenticated_keys = [
            AuthenticatedAgentKeyRecord(
                agent_id=f"agent-{canonical_player_id}",
                key_hash=api_key.key_hash,
                is_active=bool(api_key.is_active),
            )
            for player in sorted(
                players_by_match.get(match_id, []),
                key=lambda persisted: str(persisted.id),
            )
            if player.is_agent
            and player.api_key_id is not None
            and (api_key := api_keys_by_id.get(str(player.api_key_id))) is not None
            and (canonical_player_id := persisted_player_mapping.get(str(player.id))) is not None
        ]
        if authenticated_keys:
            authenticated_keys_by_match[match_id] = authenticated_keys

    return authenticated_keys_by_match


def _load_joined_agents_by_match(
    *,
    matches: Sequence[Match],
    player_rows: Sequence[Player],
) -> dict[str, dict[str, str]]:
    players_by_match: dict[str, list[Player]] = defaultdict(list)
    for player in player_rows:
        players_by_match[str(player.match_id)].append(player)

    joined_agents_by_match: dict[str, dict[str, str]] = {}
    for match in matches:
        match_id = str(match.id)
        state = MatchState.model_validate(match.state)
        persisted_player_mapping = _build_persisted_player_mapping(
            canonical_player_ids=sorted(state.players),
            persisted_players=players_by_match.get(match_id, []),
        )
        joined_agents = {
            f"agent-{canonical_player_id}": canonical_player_id
            for player in players_by_match.get(match_id, [])
            if player.is_agent
            and (canonical_player_id := persisted_player_mapping.get(str(player.id))) is not None
        }
        if joined_agents:
            joined_agents_by_match[match_id] = joined_agents

    return joined_agents_by_match


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
