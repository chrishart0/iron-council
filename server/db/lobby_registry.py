from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from server.agent_registry import (
    AuthenticatedAgentKeyRecord,
    InMemoryMatchRegistry,
    MatchJoinError,
    MatchRecord,
)
from server.db.agent_entitlements import (
    AGENT_ENTITLEMENT_REQUIRED_CODE,
    AGENT_ENTITLEMENT_REQUIRED_MESSAGE,
)
from server.db.hydration import load_match_record_from_session
from server.db.hydration import (
    load_match_registry_from_database as _load_match_registry_from_database,
)
from server.db.identity import (
    ResolvedAuthenticatedDbAgent,
    get_api_key_match_occupancy_entitlement,
    resolve_authenticated_agent_from_db_key_hash,
    resolve_human_display_name,
    resolve_human_elo_rating,
)
from server.db.models import Match, Player
from server.db.player_ids import build_human_actor_id, build_match_scoped_player_id
from server.match_initialization import (
    MatchConfig,
    MatchInitializationError,
    MatchRosterEntry,
    initialize_match_state,
)
from server.models.api import (
    AgentProfileHistory,
    AgentProfileRating,
    AgentProfileResponse,
    AuthenticatedAgentContext,
    MatchJoinResponse,
    MatchLobbyCreateRequest,
    MatchLobbyCreateResponse,
    MatchLobbyStartResponse,
    empty_treaty_reputation,
)
from server.models.domain import MatchStatus
from server.models.state import ResourceState


class MatchLobbyCreationError(Exception):
    def __init__(self, *, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class MatchLobbyStartError(Exception):
    def __init__(self, *, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class CreatedMatchLobby:
    response: MatchLobbyCreateResponse
    record: MatchRecord


@dataclass(frozen=True)
class StartedMatchLobby:
    response: MatchLobbyStartResponse
    record: MatchRecord


@dataclass(frozen=True)
class JoinedMatch:
    response: MatchJoinResponse
    record: MatchRecord


def _raise_match_lobby_creation_occupancy_limit_error() -> None:
    raise MatchLobbyCreationError(
        code="api_key_match_occupancy_limit_reached",
        message="API key already occupies the maximum number of lobby or active matches.",
    )


def _raise_match_join_occupancy_limit_error() -> None:
    raise MatchJoinError(
        code="api_key_match_occupancy_limit_reached",
        message="API key already occupies the maximum number of lobby or active matches.",
    )


def _raise_match_entitlement_required_error() -> None:
    raise MatchLobbyCreationError(
        code=AGENT_ENTITLEMENT_REQUIRED_CODE,
        message=AGENT_ENTITLEMENT_REQUIRED_MESSAGE,
    )


def _raise_match_join_entitlement_required_error() -> None:
    raise MatchJoinError(
        code=AGENT_ENTITLEMENT_REQUIRED_CODE,
        message=AGENT_ENTITLEMENT_REQUIRED_MESSAGE,
    )


def load_match_registry_from_database(database_url: str) -> InMemoryMatchRegistry:
    return _load_match_registry_from_database(database_url)


def create_match_lobby(
    *,
    database_url: str,
    authenticated_agent_id: str | None = None,
    authenticated_agent_display_name: str | None = None,
    authenticated_api_key_hash: str | None = None,
    authenticated_human_user_id: str | None = None,
    request: MatchLobbyCreateRequest,
) -> CreatedMatchLobby:
    creator_player_id = "player-1"
    roster = [
        MatchRosterEntry(player_id=f"player-{player_index}")
        for player_index in range(1, request.max_players + 1)
    ]
    config = MatchConfig(
        victory_city_threshold=request.victory_city_threshold,
        starting_cities_per_player=request.starting_cities_per_player,
        starting_resources=ResourceState(food=120, production=85, money=200),
    )
    try:
        initial_state = initialize_match_state(config, roster)
    except MatchInitializationError as exc:
        raise MatchLobbyCreationError(
            code="invalid_match_lobby_config",
            message=str(exc),
        ) from exc

    match_id = str(uuid4())
    creator_api_key_id: str | None = None
    creator_user_id: str | None = None
    creator_elo_rating = 0
    resolved_authenticated_agent: AuthenticatedAgentContext | None = None
    creator_display_name: str | None = None
    creator_is_agent = False
    engine = create_engine(database_url)
    with Session(engine) as session, session.begin():
        if authenticated_api_key_hash is not None:
            authenticated_agent_resolution = resolve_authenticated_agent_from_db_key_hash(
                session=session,
                key_hash=authenticated_api_key_hash,
            )
            if authenticated_agent_resolution is None:
                raise MatchLobbyCreationError(
                    code="invalid_api_key",
                    message="A valid active X-API-Key header is required.",
                )
            occupancy_entitlement = get_api_key_match_occupancy_entitlement(
                session=session,
                api_key_id=authenticated_agent_resolution.api_key_id,
            )
            if not occupancy_entitlement.entitlement.is_entitled:
                _raise_match_entitlement_required_error()
            if not occupancy_entitlement.has_capacity:
                _raise_match_lobby_creation_occupancy_limit_error()
            resolved_authenticated_agent = authenticated_agent_resolution.context
            creator_api_key_id = authenticated_agent_resolution.api_key_id
            creator_user_id = authenticated_agent_resolution.user_id
            creator_elo_rating = authenticated_agent_resolution.elo_rating
            creator_display_name = authenticated_agent_resolution.context.display_name
            creator_is_agent = True
        elif authenticated_human_user_id is not None:
            creator_user_id = authenticated_human_user_id
            creator_display_name = resolve_human_display_name(
                session=session,
                user_id=authenticated_human_user_id,
            )
            creator_elo_rating = resolve_human_elo_rating(
                session=session,
                user_id=authenticated_human_user_id,
            )
        else:
            raise MatchLobbyCreationError(
                code="invalid_player_auth",
                message="Player routes require a valid Bearer token or active X-API-Key header.",
            )

        session.add(
            Match(
                id=match_id,
                config={
                    "map": request.map,
                    "max_players": request.max_players,
                    "turn_seconds": request.tick_interval_seconds,
                    "victory_city_threshold": request.victory_city_threshold,
                    "starting_cities_per_player": request.starting_cities_per_player,
                    "creator_api_key_id": creator_api_key_id,
                    "creator_user_id": creator_user_id,
                },
                status=MatchStatus.LOBBY.value,
                current_tick=initial_state.tick,
                state=initial_state.model_dump(mode="json"),
                winner_alliance=None,
            )
        )
        session.add(
            Player(
                id=build_match_scoped_player_id(match_id=match_id, join_index=1),
                user_id=creator_user_id,
                match_id=match_id,
                display_name=creator_display_name or authenticated_human_user_id or "Human player",
                is_agent=creator_is_agent,
                api_key_id=creator_api_key_id,
                elo_rating=creator_elo_rating,
                alliance_id=None,
                alliance_joined_tick=None,
                eliminated_at=None,
            )
        )

    creator_profile: AgentProfileResponse | None = None
    if creator_is_agent:
        creator_agent_id = (
            resolved_authenticated_agent.agent_id
            if resolved_authenticated_agent is not None
            else authenticated_agent_id
        )
        creator_agent_display_name = (
            resolved_authenticated_agent.display_name
            if resolved_authenticated_agent is not None
            else authenticated_agent_display_name
        )
        assert creator_agent_id is not None
        assert creator_agent_display_name is not None
        creator_profile = AgentProfileResponse(
            agent_id=creator_agent_id,
            display_name=creator_agent_display_name,
            is_seeded=resolved_authenticated_agent.is_seeded
            if resolved_authenticated_agent is not None
            else True,
            rating=AgentProfileRating(elo=creator_elo_rating, provisional=True),
            history=AgentProfileHistory(matches_played=0, wins=0, losses=0, draws=0),
            treaty_reputation=empty_treaty_reputation(),
        )

    return CreatedMatchLobby(
        response=MatchLobbyCreateResponse(
            match_id=match_id,
            status=MatchStatus.LOBBY,
            map=request.map,
            tick=initial_state.tick,
            tick_interval_seconds=request.tick_interval_seconds,
            current_player_count=1,
            max_player_count=request.max_players,
            open_slot_count=max(request.max_players - 1, 0),
            creator_player_id=creator_player_id,
        ),
        record=MatchRecord(
            match_id=match_id,
            status=MatchStatus.LOBBY,
            tick_interval_seconds=request.tick_interval_seconds,
            state=initial_state,
            map_id=request.map,
            max_player_count=request.max_players,
            current_player_count=1,
            joinable_player_ids=[
                f"player-{player_index}" for player_index in range(2, request.max_players + 1)
            ],
            agent_profiles=[creator_profile] if creator_profile is not None else [],
            public_competitor_kinds={creator_player_id: "agent" if creator_is_agent else "human"},
            joined_agents=(
                {creator_profile.agent_id: creator_player_id} if creator_profile is not None else {}
            ),
            joined_humans=(
                {authenticated_human_user_id: creator_player_id}
                if authenticated_human_user_id is not None
                else {}
            ),
            authenticated_agent_keys=(
                [
                    AuthenticatedAgentKeyRecord(
                        agent_id=creator_profile.agent_id,
                        key_hash=authenticated_api_key_hash,
                        is_active=True,
                    )
                ]
                if creator_profile is not None and authenticated_api_key_hash is not None
                else []
            ),
        ),
    )


def join_match(
    *,
    database_url: str,
    match_id: str,
    authenticated_api_key_hash: str | None = None,
    authenticated_human_user_id: str | None = None,
) -> JoinedMatch:
    engine = create_engine(database_url)
    with Session(engine) as session, session.begin():
        match = session.get(Match, match_id)
        if match is None:
            raise MatchJoinError(
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )

        joined_record = load_match_record_from_session(session=session, match=match)
        assigned_player_id = (
            joined_record.joinable_player_ids[0] if joined_record.joinable_player_ids else None
        )

        if authenticated_api_key_hash is not None:
            authenticated_agent_resolution = resolve_authenticated_agent_from_db_key_hash(
                session=session,
                key_hash=authenticated_api_key_hash,
            )
            if authenticated_agent_resolution is None:
                raise MatchJoinError(
                    code="invalid_api_key",
                    message="A valid active X-API-Key header is required.",
                )

            existing_player_id = joined_record.joined_agents.get(
                authenticated_agent_resolution.context.agent_id
            )
            if existing_player_id is not None:
                return JoinedMatch(
                    response=MatchJoinResponse(
                        status="accepted",
                        match_id=match_id,
                        agent_id=authenticated_agent_resolution.context.agent_id,
                        player_id=existing_player_id,
                    ),
                    record=joined_record,
                )

            if match.status in {MatchStatus.LOBBY.value, MatchStatus.ACTIVE.value}:
                occupancy_entitlement = get_api_key_match_occupancy_entitlement(
                    session=session,
                    api_key_id=authenticated_agent_resolution.api_key_id,
                )
                if not occupancy_entitlement.entitlement.is_entitled:
                    _raise_match_join_entitlement_required_error()
                if not occupancy_entitlement.has_capacity:
                    _raise_match_join_occupancy_limit_error()

            if assigned_player_id is None:
                raise MatchJoinError(
                    code="match_not_joinable",
                    message=f"Match '{match_id}' does not support agent joins.",
                )

            session.add(
                Player(
                    id=build_match_scoped_player_id(
                        match_id=match_id,
                        join_index=len(joined_record.joined_agents)
                        + len(joined_record.joined_humans)
                        + 1,
                    ),
                    user_id=authenticated_agent_resolution.user_id,
                    match_id=match_id,
                    display_name=authenticated_agent_resolution.context.display_name,
                    is_agent=True,
                    api_key_id=authenticated_agent_resolution.api_key_id,
                    elo_rating=authenticated_agent_resolution.elo_rating,
                    alliance_id=None,
                    alliance_joined_tick=None,
                    eliminated_at=None,
                )
            )
            updated_record = load_match_record_from_session(session=session, match=match)
            return JoinedMatch(
                response=MatchJoinResponse(
                    status="accepted",
                    match_id=match_id,
                    agent_id=authenticated_agent_resolution.context.agent_id,
                    player_id=assigned_player_id,
                ),
                record=updated_record,
            )

        if authenticated_human_user_id is None:
            raise MatchJoinError(
                code="invalid_player_auth",
                message="Player routes require a valid Bearer token or active X-API-Key header.",
            )

        existing_player_id = joined_record.joined_humans.get(authenticated_human_user_id)
        if existing_player_id is not None:
            return JoinedMatch(
                response=MatchJoinResponse(
                    status="accepted",
                    match_id=match_id,
                    agent_id=build_human_actor_id(authenticated_human_user_id),
                    player_id=existing_player_id,
                ),
                record=joined_record,
            )

        if assigned_player_id is None:
            raise MatchJoinError(
                code="match_not_joinable",
                message=f"Match '{match_id}' does not support player joins.",
            )

        session.add(
            Player(
                id=build_match_scoped_player_id(
                    match_id=match_id,
                    join_index=len(joined_record.joined_agents)
                    + len(joined_record.joined_humans)
                    + 1,
                ),
                user_id=authenticated_human_user_id,
                match_id=match_id,
                display_name=resolve_human_display_name(
                    session=session,
                    user_id=authenticated_human_user_id,
                ),
                is_agent=False,
                api_key_id=None,
                elo_rating=resolve_human_elo_rating(
                    session=session,
                    user_id=authenticated_human_user_id,
                ),
                alliance_id=None,
                alliance_joined_tick=None,
                eliminated_at=None,
            )
        )
        updated_record = load_match_record_from_session(session=session, match=match)

    return JoinedMatch(
        response=MatchJoinResponse(
            status="accepted",
            match_id=match_id,
            agent_id=build_human_actor_id(authenticated_human_user_id),
            player_id=assigned_player_id,
        ),
        record=updated_record,
    )


def start_match_lobby(
    *,
    database_url: str,
    match_id: str,
    authenticated_api_key_hash: str | None = None,
    authenticated_human_user_id: str | None = None,
) -> StartedMatchLobby:
    engine = create_engine(database_url)
    with Session(engine) as session, session.begin():
        authenticated_agent_resolution: ResolvedAuthenticatedDbAgent | None = None
        if authenticated_api_key_hash is not None:
            authenticated_agent_resolution = resolve_authenticated_agent_from_db_key_hash(
                session=session,
                key_hash=authenticated_api_key_hash,
            )
            if authenticated_agent_resolution is None:
                raise MatchLobbyStartError(
                    code="invalid_api_key",
                    message="A valid active X-API-Key header is required.",
                )
        elif authenticated_human_user_id is None:
            raise MatchLobbyStartError(
                code="invalid_player_auth",
                message="Player routes require a valid Bearer token or active X-API-Key header.",
            )

        match = session.get(Match, match_id)
        if match is None:
            raise MatchLobbyStartError(
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )

        if match.status == MatchStatus.ACTIVE.value:
            raise MatchLobbyStartError(
                code="match_already_active",
                message=f"Match '{match_id}' is already active.",
            )
        if match.status == MatchStatus.COMPLETED.value:
            raise MatchLobbyStartError(
                code="match_already_completed",
                message=f"Match '{match_id}' is already completed.",
            )
        if match.status != MatchStatus.LOBBY.value:
            raise MatchLobbyStartError(
                code="match_not_startable",
                message=f"Match '{match_id}' cannot be started from status '{match.status}'.",
            )

        raw_creator_api_key_id = match.config.get("creator_api_key_id")
        creator_api_key_id = (
            raw_creator_api_key_id
            if isinstance(raw_creator_api_key_id, str) and raw_creator_api_key_id
            else None
        )
        raw_creator_user_id = match.config.get("creator_user_id")
        creator_user_id = (
            raw_creator_user_id
            if isinstance(raw_creator_user_id, str) and raw_creator_user_id
            else None
        )
        if authenticated_api_key_hash is not None:
            assert authenticated_agent_resolution is not None
            if creator_api_key_id != authenticated_agent_resolution.api_key_id:
                raise MatchLobbyStartError(
                    code="match_start_forbidden",
                    message=f"Authenticated agent does not own lobby '{match_id}'.",
                )
        elif authenticated_human_user_id is not None:
            if creator_user_id != authenticated_human_user_id or creator_api_key_id is not None:
                raise MatchLobbyStartError(
                    code="match_start_forbidden",
                    message=f"Authenticated human does not own lobby '{match_id}'.",
                )

        player_count = session.scalar(
            select(func.count()).select_from(Player).where(Player.match_id == match_id)
        )
        if int(player_count or 0) < 2:
            raise MatchLobbyStartError(
                code="match_lobby_not_ready",
                message=f"Match '{match_id}' needs at least 2 joined players before it can start.",
            )

        match.status = MatchStatus.ACTIVE.value
        session.add(match)
        started_record = load_match_record_from_session(session=session, match=match)

    return StartedMatchLobby(
        response=MatchLobbyStartResponse(
            match_id=started_record.match_id,
            status=started_record.status,
            map=started_record.map_id,
            tick=started_record.state.tick,
            tick_interval_seconds=started_record.tick_interval_seconds,
            current_player_count=started_record.public_current_player_count,
            max_player_count=started_record.public_max_player_count,
            open_slot_count=started_record.public_open_slot_count,
        ),
        record=started_record,
    )
