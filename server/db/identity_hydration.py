from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Literal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from server.agent_registry import (
    AuthenticatedAgentKeyRecord,
    build_seeded_profiles_by_key_hash,
)
from server.db.identity import parse_human_actor_id, resolve_loaded_agent_identity
from server.db.models import ApiKey, Match, Player, PlayerMatchSettlement
from server.db.player_ids import build_human_actor_id, build_persisted_player_mapping
from server.db.rating_settlement import SettlementAggregate, load_settlement_aggregates_by_identity
from server.models.api import (
    AgentProfileHistory,
    AgentProfileRating,
    AgentProfileResponse,
    HumanProfileResponse,
)
from server.models.state import MatchState


def load_agent_profiles_by_match(
    *,
    matches: Sequence[Match],
    player_rows: Sequence[Player],
    api_key_rows: Sequence[ApiKey],
    settlement_rows: Sequence[PlayerMatchSettlement] = (),
) -> dict[str, list[AgentProfileResponse]]:
    players_by_match: dict[str, list[Player]] = defaultdict(list)
    profiles_by_agent_id = _build_agent_profiles_by_agent_id(
        player_rows=player_rows,
        api_key_rows=api_key_rows,
        settlement_rows=settlement_rows,
    )
    profiles_by_identity = {profile.agent_id: profile for profile in profiles_by_agent_id.values()}
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
            loaded_profiles[agent_identity.agent_id] = profiles_by_identity[agent_identity.agent_id]
        profiles_by_match[match_id] = [
            loaded_profiles[agent_id] for agent_id in sorted(loaded_profiles)
        ]

    return profiles_by_match


def get_agent_profile_from_db(*, database_url: str, agent_id: str) -> AgentProfileResponse | None:
    engine = create_engine(database_url)
    with Session(engine) as session:
        player_rows = session.scalars(
            select(Player).where(Player.is_agent.is_(True)).order_by(Player.match_id, Player.id)
        ).all()
        api_key_ids = [player.api_key_id for player in player_rows if player.api_key_id is not None]
        api_key_rows = (
            session.scalars(
                select(ApiKey).where(ApiKey.id.in_(api_key_ids)).order_by(ApiKey.id)
            ).all()
            if api_key_ids
            else []
        )
        settlement_rows = session.scalars(
            select(PlayerMatchSettlement)
            .where(PlayerMatchSettlement.is_agent.is_(True))
            .order_by(PlayerMatchSettlement.settled_at, PlayerMatchSettlement.player_id)
        ).all()

    profiles_by_agent_id = _build_agent_profiles_by_agent_id(
        player_rows=player_rows,
        api_key_rows=api_key_rows,
        settlement_rows=settlement_rows,
    )
    return profiles_by_agent_id.get(agent_id)


def get_human_profile_from_db(*, database_url: str, human_id: str) -> HumanProfileResponse | None:
    user_id = parse_human_actor_id(human_id)
    if user_id is None:
        return None

    engine = create_engine(database_url)
    with Session(engine) as session:
        settlement_rows = session.scalars(
            select(PlayerMatchSettlement)
            .where(
                PlayerMatchSettlement.is_agent.is_(False),
                PlayerMatchSettlement.user_id == user_id,
            )
            .order_by(PlayerMatchSettlement.settled_at, PlayerMatchSettlement.player_id)
        ).all()
        player_rows = session.scalars(
            select(Player)
            .where(Player.is_agent.is_(False), Player.user_id == user_id)
            .order_by(Player.match_id, Player.id)
        ).all()

    settlement_aggregate = load_settlement_aggregates_by_identity(settlement_rows).get(human_id)
    if settlement_aggregate is not None:
        return HumanProfileResponse(
            human_id=human_id,
            display_name=settlement_aggregate.display_name,
            rating=AgentProfileRating(
                elo=settlement_aggregate.elo,
                provisional=settlement_aggregate.provisional,
            ),
            history=AgentProfileHistory(
                matches_played=settlement_aggregate.matches_played,
                wins=settlement_aggregate.wins,
                losses=settlement_aggregate.losses,
                draws=settlement_aggregate.draws,
            ),
        )

    player = next(iter(player_rows), None)
    if player is None:
        return None

    return HumanProfileResponse(
        human_id=build_human_actor_id(str(player.user_id)),
        display_name=player.display_name,
        rating=AgentProfileRating(elo=int(player.elo_rating), provisional=True),
        history=AgentProfileHistory(matches_played=0, wins=0, losses=0, draws=0),
    )


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


def _build_agent_profiles_by_agent_id(
    *,
    player_rows: Sequence[Player],
    api_key_rows: Sequence[ApiKey],
    settlement_rows: Sequence[PlayerMatchSettlement],
) -> dict[str, AgentProfileResponse]:
    api_keys_by_id = {str(api_key.id): api_key for api_key in api_key_rows}
    seeded_profiles_by_key_hash = build_seeded_profiles_by_key_hash()
    settlement_aggregates_by_identity = load_settlement_aggregates_by_identity(
        [settlement for settlement in settlement_rows if settlement.is_agent]
    )

    profiles_by_agent_id: dict[str, AgentProfileResponse] = {}
    for player in sorted(player_rows, key=lambda persisted: str(persisted.id)):
        if not player.is_agent:
            continue
        api_key = (
            api_keys_by_id.get(str(player.api_key_id)) if player.api_key_id is not None else None
        )
        agent_identity = resolve_loaded_agent_identity(
            player=player,
            api_key=api_key,
            seeded_profiles_by_key_hash=seeded_profiles_by_key_hash,
        )
        settlement_aggregate = settlement_aggregates_by_identity.get(
            _player_competitor_identity(player)
        )
        profiles_by_agent_id[agent_identity.agent_id] = _build_agent_profile(
            agent_id=agent_identity.agent_id,
            is_seeded=agent_identity.is_seeded,
            player=player,
            settlement_aggregate=settlement_aggregate,
        )
    return profiles_by_agent_id


def _build_agent_profile(
    *,
    agent_id: str,
    is_seeded: bool,
    player: Player,
    settlement_aggregate: SettlementAggregate | None,
) -> AgentProfileResponse:
    if settlement_aggregate is None:
        return AgentProfileResponse(
            agent_id=agent_id,
            display_name=player.display_name,
            is_seeded=is_seeded,
            rating=AgentProfileRating(elo=int(player.elo_rating), provisional=True),
            history=AgentProfileHistory(matches_played=0, wins=0, losses=0, draws=0),
        )

    return AgentProfileResponse(
        agent_id=agent_id,
        display_name=settlement_aggregate.display_name,
        is_seeded=is_seeded,
        rating=AgentProfileRating(
            elo=settlement_aggregate.elo,
            provisional=settlement_aggregate.provisional,
        ),
        history=AgentProfileHistory(
            matches_played=settlement_aggregate.matches_played,
            wins=settlement_aggregate.wins,
            losses=settlement_aggregate.losses,
            draws=settlement_aggregate.draws,
        ),
    )


def _player_competitor_identity(player: Player) -> str:
    if player.api_key_id is not None:
        return f"agent:{player.api_key_id}"
    return f"agent-user:{player.user_id}"


__all__ = [
    "get_agent_profile_from_db",
    "get_human_profile_from_db",
    "load_agent_profiles_by_match",
    "load_authenticated_agent_keys_by_match",
    "load_joined_agents_by_match",
    "load_joined_humans_by_match",
    "load_public_competitor_kinds_by_match",
]
