from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Literal

from server.agent_registry import (
    AuthenticatedAgentKeyRecord,
    build_seeded_profiles_by_key_hash,
)
from server.db.identity import resolve_loaded_agent_identity
from server.db.models import ApiKey, Match, Player
from server.db.player_ids import build_persisted_player_mapping
from server.models.api import AgentProfileHistory, AgentProfileRating, AgentProfileResponse
from server.models.state import MatchState


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


__all__ = [
    "load_agent_profiles_by_match",
    "load_authenticated_agent_keys_by_match",
    "load_joined_agents_by_match",
    "load_joined_humans_by_match",
    "load_public_competitor_kinds_by_match",
]
