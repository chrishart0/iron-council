from __future__ import annotations

from sqlalchemy.orm import Session

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
from server.models.api import AuthenticatedAgentContext


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
resolve_authenticated_agent_from_db_key_hash = _resolve_authenticated_agent_from_db_key_hash
resolve_human_display_name = _resolve_human_display_name
resolve_human_elo_rating = _resolve_human_elo_rating
resolve_loaded_agent_identity = _resolve_loaded_agent_identity


__all__ = [
    "ResolvedAuthenticatedDbAgent",
    "build_human_actor_id",
    "build_joined_player_id",
    "build_match_scoped_player_id",
    "build_persisted_player_mapping",
    "resolve_authenticated_agent_context_from_db",
    "resolve_authenticated_agent_from_db_key_hash",
    "resolve_human_display_name",
    "resolve_human_elo_rating",
    "resolve_human_player_id_from_db",
    "resolve_loaded_agent_identity",
]
