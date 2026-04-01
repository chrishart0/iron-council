from __future__ import annotations

from server.agent_registry_types import MatchAccessError, MatchJoinError, MatchRecord
from server.auth import hash_api_key
from server.models.api import (
    AuthenticatedAgentContext,
    MatchJoinResponse,
)


def seed_authenticated_agent_key(
    *,
    agent: AuthenticatedAgentContext,
    key_hash: str,
    is_active: bool,
    authenticated_agents_by_key_hash: dict[str, AuthenticatedAgentContext],
    agent_api_key_hashes_by_agent_id: dict[str, set[str]],
) -> None:
    agent_api_key_hashes_by_agent_id.setdefault(agent.agent_id, set()).add(key_hash)
    if is_active:
        authenticated_agents_by_key_hash[key_hash] = agent.model_copy(deep=True)


def resolve_authenticated_agent(
    *,
    api_key: str,
    authenticated_agents_by_key_hash: dict[str, AuthenticatedAgentContext],
) -> AuthenticatedAgentContext | None:
    authenticated_agent = authenticated_agents_by_key_hash.get(hash_api_key(api_key))
    if authenticated_agent is None:
        return None
    return authenticated_agent.model_copy(deep=True)


def deactivate_agent_api_key(
    *,
    agent_id: str,
    authenticated_agents_by_key_hash: dict[str, AuthenticatedAgentContext],
    agent_api_key_hashes_by_agent_id: dict[str, set[str]],
) -> None:
    for key_hash in agent_api_key_hashes_by_agent_id.get(agent_id, set()):
        authenticated_agents_by_key_hash.pop(key_hash, None)


def join_match(*, record: MatchRecord, match_id: str, agent_id: str) -> MatchJoinResponse:
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


def require_joined_player_id(
    *,
    record: MatchRecord | None,
    match_id: str,
    agent_id: str,
) -> str:
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


def require_joined_human_player_id(
    *,
    record: MatchRecord | None,
    match_id: str,
    user_id: str,
) -> str:
    if record is None:
        raise MatchAccessError(
            code="match_not_found",
            message=f"Match '{match_id}' was not found.",
        )

    player_id = record.joined_humans.get(user_id)
    if player_id is None:
        raise MatchAccessError(
            code="human_not_joined",
            message=f"Human user '{user_id}' has not joined match '{match_id}' as a player.",
        )
    return player_id
