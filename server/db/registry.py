from __future__ import annotations

from server.db.hydration import (
    load_agent_profiles_by_match,
    load_authenticated_agent_keys_by_match,
    load_joined_agents_by_match,
    load_joined_humans_by_match,
    load_match_record_from_session,
    load_match_registry_from_database,
    load_persisted_alliances_by_match,
    load_public_competitor_kinds_by_match,
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
from server.db.identity_hydration import get_human_profile_from_db
from server.db.identity_registry import (
    ResolvedAuthenticatedDbAgent,
    build_human_actor_id,
    build_joined_player_id,
    build_match_scoped_player_id,
    build_persisted_player_mapping,
    resolve_authenticated_agent_context_from_db,
    resolve_authenticated_agent_from_db_key_hash,
    resolve_human_display_name,
    resolve_human_elo_rating,
    resolve_human_player_id_from_db,
    resolve_loaded_agent_identity,
)
from server.db.identity_registry import (
    build_human_actor_id as _build_human_actor_id,
)
from server.db.identity_registry import (
    build_joined_player_id as _build_joined_player_id,
)
from server.db.identity_registry import (
    build_match_scoped_player_id as _build_match_scoped_player_id,
)
from server.db.identity_registry import (
    build_persisted_player_mapping as _build_persisted_player_mapping,
)
from server.db.lobby_registry import (
    CreatedMatchLobby,
    JoinedMatch,
    MatchLobbyCreationError,
    MatchLobbyStartError,
    StartedMatchLobby,
    create_match_lobby,
    join_match,
    start_match_lobby,
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
from server.db.tick_persistence import persist_advanced_match_tick

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
    "_build_human_actor_id",
    "_build_joined_player_id",
    "_build_match_scoped_player_id",
    "_build_persisted_player_mapping",
    "_load_agent_profiles_by_match",
    "_load_authenticated_agent_keys_by_match",
    "_load_joined_agents_by_match",
    "_load_joined_humans_by_match",
    "_load_match_record_from_session",
    "_load_persisted_alliances_by_match",
    "_load_public_competitor_kinds_by_match",
    "_resolve_authenticated_agent_context_from_db",
    "_resolve_authenticated_agent_from_db_key_hash",
    "_resolve_human_display_name",
    "_resolve_human_elo_rating",
    "_resolve_human_player_id_from_db",
    "_resolve_loaded_agent_identity",
    "build_human_actor_id",
    "build_joined_player_id",
    "build_match_scoped_player_id",
    "build_persisted_player_mapping",
    "create_match_lobby",
    "get_completed_match_summaries",
    "get_match_history",
    "get_match_replay_tick",
    "get_human_profile_from_db",
    "get_public_leaderboard",
    "get_public_match_detail",
    "get_public_match_summaries",
    "join_match",
    "load_agent_profiles_by_match",
    "load_authenticated_agent_keys_by_match",
    "load_joined_agents_by_match",
    "load_joined_humans_by_match",
    "load_match_record_from_session",
    "load_match_registry_from_database",
    "load_persisted_alliances_by_match",
    "load_public_competitor_kinds_by_match",
    "persist_advanced_match_tick",
    "resolve_authenticated_agent_context_from_db",
    "resolve_authenticated_agent_from_db_key_hash",
    "resolve_human_display_name",
    "resolve_human_elo_rating",
    "resolve_human_player_id_from_db",
    "resolve_loaded_agent_identity",
    "start_match_lobby",
]
