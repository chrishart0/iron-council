from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Literal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from server import agent_registry_diplomacy
from server.agent_registry import (
    AuthenticatedAgentKeyRecord,
    InMemoryMatchRegistry,
    MatchAlliance,
    MatchAllianceMember,
    MatchRecord,
    build_seeded_agent_profiles,
    build_seeded_profiles_by_key_hash,
)
from server.db.identity import resolve_loaded_agent_identity
from server.db.models import Alliance, ApiKey, Match, Player
from server.db.player_ids import build_persisted_player_mapping
from server.models.api import AgentProfileHistory, AgentProfileRating, AgentProfileResponse
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
        api_key_rows = session.scalars(select(ApiKey).order_by(ApiKey.id)).all()

        alliances_by_match = load_persisted_alliances_by_match(
            matches=matches,
            alliance_rows=alliance_rows,
            player_rows=player_rows,
        )
        agent_profiles_by_match = load_agent_profiles_by_match(
            matches=matches,
            player_rows=player_rows,
            api_key_rows=api_key_rows,
        )
        authenticated_keys_by_match = load_authenticated_agent_keys_by_match(
            matches=matches,
            player_rows=player_rows,
            api_key_rows=api_key_rows,
        )
        joined_agents_by_match = load_joined_agents_by_match(
            matches=matches,
            player_rows=player_rows,
            api_key_rows=api_key_rows,
        )
        joined_humans_by_match = load_joined_humans_by_match(
            matches=matches,
            player_rows=player_rows,
        )
        public_competitor_kinds_by_match = load_public_competitor_kinds_by_match(
            matches=matches,
            player_rows=player_rows,
        )

        for match in matches:
            match_id = str(match.id)
            persisted_alliances = alliances_by_match.get(match_id, [])
            state = MatchState.model_validate(match.state)
            joined_agents = joined_agents_by_match.get(match_id, {})
            joined_humans = joined_humans_by_match.get(match_id, {})
            record = MatchRecord(
                match_id=match_id,
                status=MatchStatus(match.status),
                tick_interval_seconds=int(match.config.get("turn_seconds", 0)),
                state=state,
                map_id=str(match.config.get("map", "britain")),
                max_player_count=int(match.config.get("max_players", len(state.players))),
                current_player_count=len(joined_agents) + len(joined_humans),
                joinable_player_ids=(
                    sorted(
                        player_id
                        for player_id in state.players
                        if player_id not in joined_agents.values()
                        and player_id not in joined_humans.values()
                    )
                    if match.status in {MatchStatus.LOBBY.value, MatchStatus.PAUSED.value}
                    else []
                ),
                agent_profiles=agent_profiles_by_match.get(match_id, build_seeded_agent_profiles()),
                public_competitor_kinds=public_competitor_kinds_by_match.get(match_id, {}),
                joined_agents=joined_agents,
                joined_humans=joined_humans,
                alliances=persisted_alliances,
                authenticated_agent_keys=authenticated_keys_by_match.get(match_id, []),
            )
            registry.seed_match(record)

    return registry


def load_match_record_from_session(*, session: Session, match: Match) -> MatchRecord:
    match_id = str(match.id)
    player_rows = session.scalars(
        select(Player).where(Player.match_id == match.id).order_by(Player.id)
    ).all()
    api_key_ids = [player.api_key_id for player in player_rows if player.api_key_id is not None]
    api_key_rows = (
        session.scalars(select(ApiKey).where(ApiKey.id.in_(api_key_ids)).order_by(ApiKey.id)).all()
        if api_key_ids
        else []
    )
    state = MatchState.model_validate(match.state)
    joined_agents = load_joined_agents_by_match(
        matches=[match],
        player_rows=player_rows,
        api_key_rows=api_key_rows,
    ).get(match_id, {})
    joined_humans = load_joined_humans_by_match(
        matches=[match],
        player_rows=player_rows,
    ).get(match_id, {})
    agent_profiles = load_agent_profiles_by_match(
        matches=[match],
        player_rows=player_rows,
        api_key_rows=api_key_rows,
    ).get(match_id, [])
    authenticated_agent_keys = load_authenticated_agent_keys_by_match(
        matches=[match],
        player_rows=player_rows,
        api_key_rows=api_key_rows,
    ).get(match_id, [])
    public_competitor_kinds = load_public_competitor_kinds_by_match(
        matches=[match],
        player_rows=player_rows,
    ).get(match_id, {})
    joinable_player_ids = (
        sorted(
            player_id
            for player_id in state.players
            if player_id not in joined_agents.values() and player_id not in joined_humans.values()
        )
        if match.status in {MatchStatus.LOBBY.value, MatchStatus.PAUSED.value}
        else []
    )
    return MatchRecord(
        match_id=match_id,
        status=MatchStatus(match.status),
        tick_interval_seconds=int(match.config.get("turn_seconds", 0)),
        state=state,
        map_id=str(match.config.get("map", "britain")),
        max_player_count=int(match.config.get("max_players", len(state.players))),
        current_player_count=len(joined_agents) + len(joined_humans),
        joinable_player_ids=joinable_player_ids,
        agent_profiles=agent_profiles,
        public_competitor_kinds=public_competitor_kinds,
        joined_agents=joined_agents,
        joined_humans=joined_humans,
        authenticated_agent_keys=authenticated_agent_keys,
    )


def load_persisted_alliances_by_match(
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
        derived_alliances = agent_registry_diplomacy.derive_alliances_from_state(state)
        persisted_player_mapping = build_persisted_player_mapping(
            canonical_player_ids=sorted(state.players),
            persisted_players=players_by_match.get(match_id, []),
        )
        persisted_rows_for_match = [
            alliance_row for alliance_row in alliance_rows if str(alliance_row.match_id) == match_id
        ]
        persisted_alliances = merge_persisted_alliance_metadata(
            derived_alliances=derived_alliances,
            persisted_rows=persisted_rows_for_match,
            players_by_match_and_alliance=players_by_match_and_alliance,
            persisted_player_mapping=persisted_player_mapping,
            match_id=match_id,
        )
        if persisted_alliances:
            alliances_by_match[match_id] = persisted_alliances

    return alliances_by_match


def load_agent_profiles_by_match(
    *,
    matches: Sequence[Match],
    player_rows: Sequence[Player],
    api_key_rows: Sequence[ApiKey],
) -> dict[str, list[AgentProfileResponse]]:
    players_by_match: dict[str, list[Player]] = defaultdict(list)
    api_keys_by_id = {str(api_key.id): api_key for api_key in api_key_rows}
    seeded_profiles_by_key_hash = build_seeded_profiles_by_key_hash()
    for player in player_rows:
        players_by_match[str(player.match_id)].append(player)

    profiles_by_match: dict[str, list[AgentProfileResponse]] = {}
    for match in matches:
        match_id = str(match.id)
        loaded_profiles: dict[str, AgentProfileResponse] = {}
        for player in sorted(
            players_by_match.get(match_id, []), key=lambda persisted: str(persisted.id)
        ):
            if not player.is_agent:
                continue
            api_key = (
                api_keys_by_id.get(str(player.api_key_id))
                if player.api_key_id is not None
                else None
            )
            agent_identity = resolve_loaded_agent_identity(
                player=player,
                api_key=api_key,
                seeded_profiles_by_key_hash=seeded_profiles_by_key_hash,
            )
            loaded_profiles[agent_identity.agent_id] = AgentProfileResponse(
                agent_id=agent_identity.agent_id,
                display_name=player.display_name,
                is_seeded=agent_identity.is_seeded,
                rating=AgentProfileRating(elo=int(player.elo_rating), provisional=True),
                history=AgentProfileHistory(matches_played=0, wins=0, losses=0, draws=0),
            )
        profiles_by_match[match_id] = [
            loaded_profiles[agent_id] for agent_id in sorted(loaded_profiles)
        ]

    return profiles_by_match


def load_authenticated_agent_keys_by_match(
    *,
    matches: Sequence[Match],
    player_rows: Sequence[Player],
    api_key_rows: Sequence[ApiKey],
) -> dict[str, list[AuthenticatedAgentKeyRecord]]:
    players_by_match: dict[str, list[Player]] = defaultdict(list)
    api_keys_by_id = {str(api_key.id): api_key for api_key in api_key_rows}
    seeded_profiles_by_key_hash = build_seeded_profiles_by_key_hash()
    for player in player_rows:
        players_by_match[str(player.match_id)].append(player)

    authenticated_keys_by_match: dict[str, list[AuthenticatedAgentKeyRecord]] = {}
    for match in matches:
        match_id = str(match.id)
        state = MatchState.model_validate(match.state)
        persisted_player_mapping = build_persisted_player_mapping(
            canonical_player_ids=sorted(state.players),
            persisted_players=players_by_match.get(match_id, []),
        )
        authenticated_keys = [
            AuthenticatedAgentKeyRecord(
                agent_id=resolve_loaded_agent_identity(
                    player=player,
                    api_key=api_key,
                    seeded_profiles_by_key_hash=seeded_profiles_by_key_hash,
                ).agent_id,
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
            and persisted_player_mapping.get(str(player.id)) is not None
        ]
        if authenticated_keys:
            authenticated_keys_by_match[match_id] = authenticated_keys

    return authenticated_keys_by_match


def load_joined_agents_by_match(
    *,
    matches: Sequence[Match],
    player_rows: Sequence[Player],
    api_key_rows: Sequence[ApiKey],
) -> dict[str, dict[str, str]]:
    players_by_match: dict[str, list[Player]] = defaultdict(list)
    api_keys_by_id = {str(api_key.id): api_key for api_key in api_key_rows}
    seeded_profiles_by_key_hash = build_seeded_profiles_by_key_hash()
    for player in player_rows:
        players_by_match[str(player.match_id)].append(player)

    joined_agents_by_match: dict[str, dict[str, str]] = {}
    for match in matches:
        match_id = str(match.id)
        state = MatchState.model_validate(match.state)
        persisted_player_mapping = build_persisted_player_mapping(
            canonical_player_ids=sorted(state.players),
            persisted_players=players_by_match.get(match_id, []),
        )
        joined_agents = {
            resolve_loaded_agent_identity(
                player=player,
                api_key=(
                    api_keys_by_id.get(str(player.api_key_id))
                    if player.api_key_id is not None
                    else None
                ),
                seeded_profiles_by_key_hash=seeded_profiles_by_key_hash,
            ).agent_id: canonical_player_id
            for player in players_by_match.get(match_id, [])
            if player.is_agent
            and (canonical_player_id := persisted_player_mapping.get(str(player.id))) is not None
        }
        if joined_agents:
            joined_agents_by_match[match_id] = joined_agents

    return joined_agents_by_match


def load_joined_humans_by_match(
    *,
    matches: Sequence[Match],
    player_rows: Sequence[Player],
) -> dict[str, dict[str, str]]:
    players_by_match: dict[str, list[Player]] = defaultdict(list)
    for player in player_rows:
        players_by_match[str(player.match_id)].append(player)

    joined_humans_by_match: dict[str, dict[str, str]] = {}
    for match in matches:
        match_id = str(match.id)
        state = MatchState.model_validate(match.state)
        persisted_player_mapping = build_persisted_player_mapping(
            canonical_player_ids=sorted(state.players),
            persisted_players=players_by_match.get(match_id, []),
        )
        joined_humans = {
            str(player.user_id): canonical_player_id
            for player in players_by_match.get(match_id, [])
            if not player.is_agent
            and (canonical_player_id := persisted_player_mapping.get(str(player.id))) is not None
        }
        if joined_humans:
            joined_humans_by_match[match_id] = joined_humans

    return joined_humans_by_match


def load_public_competitor_kinds_by_match(
    *,
    matches: Sequence[Match],
    player_rows: Sequence[Player],
) -> dict[str, dict[str, Literal["human", "agent"]]]:
    players_by_match: dict[str, list[Player]] = defaultdict(list)
    for player in player_rows:
        players_by_match[str(player.match_id)].append(player)

    competitor_kinds_by_match: dict[str, dict[str, Literal["human", "agent"]]] = {}
    for match in matches:
        match_id = str(match.id)
        state = MatchState.model_validate(match.state)
        persisted_player_mapping = build_persisted_player_mapping(
            canonical_player_ids=sorted(state.players),
            persisted_players=players_by_match.get(match_id, []),
        )
        competitor_kinds: dict[str, Literal["human", "agent"]] = {
            canonical_player_id: ("agent" if player.is_agent else "human")
            for player in players_by_match.get(match_id, [])
            if (canonical_player_id := persisted_player_mapping.get(str(player.id))) is not None
        }
        if competitor_kinds:
            competitor_kinds_by_match[match_id] = competitor_kinds

    return competitor_kinds_by_match


def merge_persisted_alliance_metadata(
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


__all__ = [
    "load_agent_profiles_by_match",
    "load_authenticated_agent_keys_by_match",
    "load_joined_agents_by_match",
    "load_joined_humans_by_match",
    "load_match_record_from_session",
    "load_match_registry_from_database",
    "load_persisted_alliances_by_match",
    "load_public_competitor_kinds_by_match",
]
