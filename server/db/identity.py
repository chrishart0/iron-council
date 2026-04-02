from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from server.agent_registry import build_seeded_profiles_by_key_hash
from server.auth import hash_api_key
from server.db.models import ApiKey, Match, Player
from server.db.player_ids import build_human_actor_id, build_persisted_player_mapping
from server.db.rating_settlement import latest_human_settled_elo
from server.models.api import AgentProfileResponse, AuthenticatedAgentContext
from server.models.state import MatchState


@dataclass(frozen=True)
class LoadedAgentIdentity:
    agent_id: str
    is_seeded: bool


@dataclass(frozen=True)
class ResolvedAuthenticatedDbAgent:
    context: AuthenticatedAgentContext
    api_key_id: str
    user_id: str
    elo_rating: int
    key_hash: str


def resolve_human_display_name(*, session: Session, user_id: str) -> str:
    existing_player = session.scalar(
        select(Player)
        .where(Player.user_id == user_id, Player.is_agent.is_(False))
        .order_by(Player.id.asc())
    )
    if existing_player is not None:
        return existing_player.display_name
    return user_id


def resolve_human_elo_rating(*, session: Session, user_id: str) -> int:
    if (settled_elo := latest_human_settled_elo(session=session, user_id=user_id)) is not None:
        return settled_elo

    existing_player = session.scalar(
        select(Player)
        .where(Player.user_id == user_id, Player.is_agent.is_(False))
        .order_by(Player.id.asc())
    )
    if existing_player is not None:
        return int(existing_player.elo_rating)
    return 0


def resolve_authenticated_agent_context_from_db(
    *, database_url: str, api_key: str, session_factory: type[Session]
) -> AuthenticatedAgentContext | None:
    from sqlalchemy import create_engine

    engine = create_engine(database_url)
    with session_factory(engine) as session:
        resolved = resolve_authenticated_agent_from_db_key_hash(
            session=session,
            key_hash=hash_api_key(api_key),
        )
    return resolved.context if resolved is not None else None


def resolve_human_player_id_from_db(
    *, database_url: str, match_id: str, user_id: str, session_factory: type[Session]
) -> str | None:
    from sqlalchemy import create_engine

    engine = create_engine(database_url)
    with session_factory(engine) as session:
        match = session.get(Match, match_id)
        if match is None:
            return None

        persisted_players = session.scalars(
            select(Player).where(Player.match_id == match_id).order_by(Player.id)
        ).all()
        state = MatchState.model_validate(match.state)
        persisted_player_mapping = build_persisted_player_mapping(
            canonical_player_ids=sorted(state.players),
            persisted_players=persisted_players,
        )
        resolved_player = next(
            (
                player
                for player in persisted_players
                if str(player.user_id) == user_id and not player.is_agent
            ),
            None,
        )
        if resolved_player is None:
            return None
        return persisted_player_mapping.get(str(resolved_player.id))


def resolve_loaded_agent_identity(
    *,
    player: Player,
    api_key: ApiKey | None,
    seeded_profiles_by_key_hash: dict[str, AgentProfileResponse],
) -> LoadedAgentIdentity:
    seeded_profile = (
        seeded_profiles_by_key_hash.get(api_key.key_hash) if api_key is not None else None
    )
    if seeded_profile is not None:
        return LoadedAgentIdentity(agent_id=seeded_profile.agent_id, is_seeded=True)
    return LoadedAgentIdentity(
        agent_id=build_non_seeded_agent_id(str(api_key.id))
        if api_key is not None
        else build_user_backed_agent_id(str(player.user_id)),
        is_seeded=False,
    )


def resolve_authenticated_agent_from_db_key_hash(
    *, session: Session, key_hash: str
) -> ResolvedAuthenticatedDbAgent | None:
    api_key = session.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash))
    if api_key is None or not api_key.is_active:
        return None

    persisted_players = session.scalars(
        select(Player).where(Player.api_key_id == api_key.id).order_by(Player.match_id, Player.id)
    ).all()
    existing_agent_player = next((player for player in persisted_players if player.is_agent), None)
    if persisted_players and existing_agent_player is None:
        return None

    seeded_profile = build_seeded_profiles_by_key_hash().get(api_key.key_hash)
    if seeded_profile is not None:
        return ResolvedAuthenticatedDbAgent(
            context=AuthenticatedAgentContext(
                agent_id=seeded_profile.agent_id,
                display_name=seeded_profile.display_name,
                is_seeded=True,
            ),
            api_key_id=str(api_key.id),
            user_id=str(api_key.user_id),
            elo_rating=int(api_key.elo_rating),
            key_hash=api_key.key_hash,
        )

    return ResolvedAuthenticatedDbAgent(
        context=AuthenticatedAgentContext(
            agent_id=build_non_seeded_agent_id(str(api_key.id)),
            display_name=(
                existing_agent_player.display_name
                if existing_agent_player is not None
                else build_non_seeded_display_name(str(api_key.id))
            ),
            is_seeded=False,
        ),
        api_key_id=str(api_key.id),
        user_id=str(api_key.user_id),
        elo_rating=int(api_key.elo_rating),
        key_hash=api_key.key_hash,
    )


def build_non_seeded_agent_id(api_key_id: str) -> str:
    return f"agent-api-key-{api_key_id}"


def build_non_seeded_display_name(api_key_id: str) -> str:
    return f"Agent {api_key_id[:8]}"


def build_user_backed_agent_id(user_id: str) -> str:
    return f"agent-user-{user_id}"


def parse_human_actor_id(human_id: str) -> str | None:
    prefix = "human:"
    if not human_id.startswith(prefix):
        return None
    user_id = human_id.removeprefix(prefix)
    return user_id or None


__all__ = [
    "LoadedAgentIdentity",
    "ResolvedAuthenticatedDbAgent",
    "build_human_actor_id",
    "build_non_seeded_agent_id",
    "build_non_seeded_display_name",
    "build_user_backed_agent_id",
    "parse_human_actor_id",
    "resolve_authenticated_agent_context_from_db",
    "resolve_authenticated_agent_from_db_key_hash",
    "resolve_human_display_name",
    "resolve_human_elo_rating",
    "resolve_human_player_id_from_db",
    "resolve_loaded_agent_identity",
]
