from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Literal

from sqlalchemy import and_, create_engine, or_, select
from sqlalchemy.orm import Session

from server import agent_registry_diplomacy
from server.agent_registry import (
    AuthenticatedAgentKeyRecord,
    InMemoryMatchRegistry,
    MatchAlliance,
    MatchAllianceMember,
    MatchRecord,
    build_seeded_agent_profiles,
)
from server.db.identity_hydration import (
    load_agent_profiles_by_match as _load_agent_profiles_by_match,
)
from server.db.identity_hydration import (
    load_authenticated_agent_keys_by_match as _load_authenticated_agent_keys_by_match,
)
from server.db.identity_hydration import (
    load_joined_agents_by_match as _load_joined_agents_by_match,
)
from server.db.identity_hydration import (
    load_joined_humans_by_match as _load_joined_humans_by_match,
)
from server.db.identity_hydration import (
    load_public_competitor_kinds_by_match as _load_public_competitor_kinds_by_match,
)
from server.db.models import Alliance, ApiKey, Match, Player, PlayerMatchSettlement
from server.db.player_ids import build_persisted_player_mapping
from server.models.api import AgentProfileResponse
from server.models.domain import MatchStatus
from server.models.state import MatchState


def _compose_loaded_match_record(
    *,
    match: Match,
    state: MatchState,
    joined_agents: dict[str, str],
    joined_humans: dict[str, str],
    agent_profiles: list[AgentProfileResponse],
    public_competitor_kinds: dict[str, Literal["human", "agent"]],
    authenticated_agent_keys: list[AuthenticatedAgentKeyRecord],
    alliances: list[MatchAlliance] | None = None,
) -> MatchRecord:
    return MatchRecord(
        match_id=str(match.id),
        status=MatchStatus(match.status),
        tick_interval_seconds=int(match.config.get("turn_seconds", 0)),
        state=state,
        map_id=str(match.config.get("map", "britain")),
        max_player_count=int(match.config.get("max_players", len(state.players))),
        current_player_count=len(joined_agents) + len(joined_humans),
        joinable_player_ids=_derive_joinable_player_ids(
            match_status=match.status,
            state=state,
            joined_agents=joined_agents,
            joined_humans=joined_humans,
        ),
        agent_profiles=agent_profiles,
        public_competitor_kinds=public_competitor_kinds,
        joined_agents=joined_agents,
        joined_humans=joined_humans,
        alliances=list(alliances or []),
        authenticated_agent_keys=authenticated_agent_keys,
    )


def _derive_joinable_player_ids(
    *,
    match_status: str,
    state: MatchState,
    joined_agents: dict[str, str],
    joined_humans: dict[str, str],
) -> list[str]:
    if match_status not in {MatchStatus.LOBBY.value, MatchStatus.PAUSED.value}:
        return []

    joined_player_ids = set(joined_agents.values()) | set(joined_humans.values())
    return sorted(player_id for player_id in state.players if player_id not in joined_player_ids)


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
        settlement_rows = session.scalars(
            select(PlayerMatchSettlement).order_by(
                PlayerMatchSettlement.settled_at,
                PlayerMatchSettlement.player_id,
            )
        ).all()

        alliances_by_match = load_persisted_alliances_by_match(
            matches=matches,
            alliance_rows=alliance_rows,
            player_rows=player_rows,
        )
        agent_profiles_by_match = load_agent_profiles_by_match(
            matches=matches,
            player_rows=player_rows,
            api_key_rows=api_key_rows,
            settlement_rows=settlement_rows,
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
            record = _compose_loaded_match_record(
                match=match,
                state=state,
                joined_agents=joined_agents,
                joined_humans=joined_humans,
                agent_profiles=agent_profiles_by_match.get(match_id, build_seeded_agent_profiles()),
                public_competitor_kinds=public_competitor_kinds_by_match.get(match_id, {}),
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
    settlement_filters = []
    api_key_ids_for_players = [
        player.api_key_id for player in player_rows if player.api_key_id is not None
    ]
    if api_key_ids_for_players:
        settlement_filters.append(
            and_(
                PlayerMatchSettlement.is_agent.is_(True),
                PlayerMatchSettlement.api_key_id.in_(api_key_ids_for_players),
            )
        )
    api_keyless_agent_user_ids = [
        player.user_id for player in player_rows if player.is_agent and player.api_key_id is None
    ]
    if api_keyless_agent_user_ids:
        settlement_filters.append(
            and_(
                PlayerMatchSettlement.is_agent.is_(True),
                PlayerMatchSettlement.api_key_id.is_(None),
                PlayerMatchSettlement.user_id.in_(api_keyless_agent_user_ids),
            )
        )
    human_user_ids = [player.user_id for player in player_rows if not player.is_agent]
    if human_user_ids:
        settlement_filters.append(
            and_(
                PlayerMatchSettlement.is_agent.is_(False),
                PlayerMatchSettlement.user_id.in_(human_user_ids),
            )
        )
    settlement_rows = (
        session.scalars(
            select(PlayerMatchSettlement)
            .where(or_(*settlement_filters))
            .order_by(PlayerMatchSettlement.settled_at, PlayerMatchSettlement.player_id)
        ).all()
        if settlement_filters
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
        settlement_rows=settlement_rows,
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
    return _compose_loaded_match_record(
        match=match,
        state=state,
        joined_agents=joined_agents,
        joined_humans=joined_humans,
        agent_profiles=agent_profiles,
        public_competitor_kinds=public_competitor_kinds,
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


load_agent_profiles_by_match = _load_agent_profiles_by_match
load_authenticated_agent_keys_by_match = _load_authenticated_agent_keys_by_match
load_joined_agents_by_match = _load_joined_agents_by_match
load_joined_humans_by_match = _load_joined_humans_by_match
load_public_competitor_kinds_by_match = _load_public_competitor_kinds_by_match


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
