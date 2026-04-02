from __future__ import annotations

from sqlalchemy.orm import Session

from server.agent_registry import (
    AdvancedMatchTick,
)
from server.db.hydration import (
    load_agent_profiles_by_match as _load_agent_profiles_by_match,
)
from server.db.hydration import (
    load_authenticated_agent_keys_by_match as _load_authenticated_agent_keys_by_match,
)
from server.db.hydration import (
    load_joined_agents_by_match as _load_joined_agents_by_match,
)
from server.db.hydration import (
    load_joined_humans_by_match as _load_joined_humans_by_match,
)
from server.db.hydration import (
    load_match_record_from_session as _load_match_record_from_session,
)
from server.db.hydration import (
    load_match_registry_from_database,
)
from server.db.hydration import (
    load_persisted_alliances_by_match as _load_persisted_alliances_by_match,
)
from server.db.hydration import (
    load_public_competitor_kinds_by_match as _load_public_competitor_kinds_by_match,
)
from server.db.identity import (
    ResolvedAuthenticatedDbAgent as _ResolvedAuthenticatedDbAgent,
)
from server.db.identity import (
    resolve_authenticated_agent_context_from_db as _resolve_authenticated_agent_context_from_db,
)
from server.db.identity import (
    resolve_authenticated_agent_from_db_key_hash as _resolve_authenticated_agent_from_db_key_hash,
)
from server.db.identity import (
    resolve_human_display_name as _resolve_human_display_name,
)
from server.db.identity import (
    resolve_human_elo_rating as _resolve_human_elo_rating,
)
from server.db.identity import (
    resolve_human_player_id_from_db as _resolve_human_player_id_from_db,
)
from server.db.identity import (
    resolve_loaded_agent_identity as _resolve_loaded_agent_identity,
)
from server.db.lobby_registry import (
    CreatedMatchLobby,
    JoinedMatch,
    MatchLobbyCreationError,
    MatchLobbyStartError,
    StartedMatchLobby,
)
from server.db.lobby_registry import (
    create_match_lobby as _create_match_lobby,
)
from server.db.lobby_registry import (
    join_match as _join_match,
)
from server.db.lobby_registry import (
    start_match_lobby as _start_match_lobby,
)
from server.db.player_ids import (
    build_human_actor_id as _build_human_actor_id,
)
from server.db.player_ids import (
    build_joined_player_id as _build_joined_player_id,
)
from server.db.player_ids import (
    build_match_scoped_player_id as _build_match_scoped_player_id,
)
from server.db.player_ids import (
    build_persisted_player_mapping as _build_persisted_player_mapping,
)
from server.db.public_reads import (
    MatchHistoryNotFoundError,
    PublicMatchDetailNotFoundError,
    TickHistoryNotFoundError,
    get_completed_match_summaries,
    get_match_history,
    get_match_replay_tick,
    get_public_leaderboard,
    get_public_match_detail,
    get_public_match_summaries,
)
from server.db.tick_persistence import (
    persist_advanced_match_tick as _persist_advanced_match_tick,
)
from server.models.api import (
    AuthenticatedAgentContext,
    MatchLobbyCreateRequest,
)


def persist_advanced_match_tick(*, database_url: str, advanced_tick: AdvancedMatchTick) -> None:
    _persist_advanced_match_tick(database_url=database_url, advanced_tick=advanced_tick)


def create_match_lobby(
    *,
    database_url: str,
    authenticated_agent_id: str | None = None,
    authenticated_agent_display_name: str | None = None,
    authenticated_api_key_hash: str | None = None,
    authenticated_human_user_id: str | None = None,
    request: MatchLobbyCreateRequest,
) -> CreatedMatchLobby:
    return _create_match_lobby(
        database_url=database_url,
        authenticated_agent_id=authenticated_agent_id,
        authenticated_agent_display_name=authenticated_agent_display_name,
        authenticated_api_key_hash=authenticated_api_key_hash,
        authenticated_human_user_id=authenticated_human_user_id,
        request=request,
    )


def join_match(
    *,
    database_url: str,
    match_id: str,
    authenticated_api_key_hash: str | None = None,
    authenticated_human_user_id: str | None = None,
) -> JoinedMatch:
    return _join_match(
        database_url=database_url,
        match_id=match_id,
        authenticated_api_key_hash=authenticated_api_key_hash,
        authenticated_human_user_id=authenticated_human_user_id,
    )


def start_match_lobby(
    *,
    database_url: str,
    match_id: str,
    authenticated_api_key_hash: str | None = None,
    authenticated_human_user_id: str | None = None,
) -> StartedMatchLobby:
    return _start_match_lobby(
        database_url=database_url,
        match_id=match_id,
        authenticated_api_key_hash=authenticated_api_key_hash,
        authenticated_human_user_id=authenticated_human_user_id,
    )


def resolve_authenticated_agent_context_from_db(
    *, database_url: str, api_key: str
) -> AuthenticatedAgentContext | None:
    return _resolve_authenticated_agent_context_from_db(
        database_url=database_url,
        api_key=api_key,
        session_factory=Session,
    )


def resolve_human_player_id_from_db(
    *, database_url: str, match_id: str, user_id: str
) -> str | None:
    return _resolve_human_player_id_from_db(
        database_url=database_url,
        match_id=match_id,
        user_id=user_id,
        session_factory=Session,
    )


ResolvedAuthenticatedDbAgent = _ResolvedAuthenticatedDbAgent
build_human_actor_id = _build_human_actor_id
build_joined_player_id = _build_joined_player_id
build_match_scoped_player_id = _build_match_scoped_player_id
build_persisted_player_mapping = _build_persisted_player_mapping
load_agent_profiles_by_match = _load_agent_profiles_by_match
load_authenticated_agent_keys_by_match = _load_authenticated_agent_keys_by_match
load_joined_agents_by_match = _load_joined_agents_by_match
load_joined_humans_by_match = _load_joined_humans_by_match
load_match_record_from_session = _load_match_record_from_session
load_persisted_alliances_by_match = _load_persisted_alliances_by_match
load_public_competitor_kinds_by_match = _load_public_competitor_kinds_by_match
resolve_authenticated_agent_from_db_key_hash = _resolve_authenticated_agent_from_db_key_hash
resolve_human_display_name = _resolve_human_display_name
resolve_human_elo_rating = _resolve_human_elo_rating
resolve_loaded_agent_identity = _resolve_loaded_agent_identity


__all__ = [
    "CreatedMatchLobby",
    "JoinedMatch",
    "MatchHistoryNotFoundError",
    "MatchLobbyCreationError",
    "MatchLobbyStartError",
    "PublicMatchDetailNotFoundError",
    "ResolvedAuthenticatedDbAgent",
    "StartedMatchLobby",
    "TickHistoryNotFoundError",
    "_ResolvedAuthenticatedDbAgent",
    "build_human_actor_id",
    "build_joined_player_id",
    "build_match_scoped_player_id",
    "build_persisted_player_mapping",
    "_build_human_actor_id",
    "_build_joined_player_id",
    "_build_match_scoped_player_id",
    "_build_persisted_player_mapping",
    "load_agent_profiles_by_match",
    "load_authenticated_agent_keys_by_match",
    "load_joined_agents_by_match",
    "load_joined_humans_by_match",
    "load_match_record_from_session",
    "_load_agent_profiles_by_match",
    "_load_authenticated_agent_keys_by_match",
    "_load_joined_agents_by_match",
    "_load_joined_humans_by_match",
    "_load_match_record_from_session",
    "load_persisted_alliances_by_match",
    "load_public_competitor_kinds_by_match",
    "_load_persisted_alliances_by_match",
    "_load_public_competitor_kinds_by_match",
    "_resolve_authenticated_agent_context_from_db",
    "resolve_authenticated_agent_from_db_key_hash",
    "_resolve_authenticated_agent_from_db_key_hash",
    "resolve_human_display_name",
    "resolve_human_elo_rating",
    "_resolve_human_display_name",
    "_resolve_human_elo_rating",
    "_resolve_human_player_id_from_db",
    "resolve_loaded_agent_identity",
    "_resolve_loaded_agent_identity",
    "create_match_lobby",
    "get_completed_match_summaries",
    "get_match_history",
    "get_match_replay_tick",
    "get_public_leaderboard",
    "get_public_match_detail",
    "get_public_match_summaries",
    "join_match",
    "load_match_registry_from_database",
    "persist_advanced_match_tick",
    "resolve_authenticated_agent_context_from_db",
    "resolve_human_player_id_from_db",
    "start_match_lobby",
]
