from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from server.agent_registry import (
    AdvancedMatchTick,
    AuthenticatedAgentKeyRecord,
    InMemoryMatchRegistry,
    MatchAlliance,
    MatchAllianceMember,
    MatchJoinError,
    MatchRecord,
    build_seeded_agent_api_key,
    build_seeded_agent_profiles,
)
from server.auth import hash_api_key
from server.db.models import Alliance, ApiKey, Match, Player, TickLog
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
    CompletedMatchSummary,
    CompletedMatchSummaryListResponse,
    LeaderboardEntry,
    MatchHistoryEntry,
    MatchHistoryResponse,
    MatchJoinResponse,
    MatchListResponse,
    MatchLobbyCreateRequest,
    MatchLobbyCreateResponse,
    MatchLobbyStartResponse,
    MatchReplayTickResponse,
    MatchSummary,
    PublicLeaderboardResponse,
    PublicMatchDetailResponse,
    PublicMatchRosterRow,
)
from server.models.domain import MatchStatus
from server.models.state import MatchState, ResourceState


class MatchHistoryNotFoundError(KeyError):
    pass


class TickHistoryNotFoundError(KeyError):
    pass


class PublicMatchDetailNotFoundError(KeyError):
    pass


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


@dataclass
class _LeaderboardAggregate:
    competitor_key: str
    display_name: str
    competitor_kind: Literal["human", "agent"]
    elo: int
    provisional: bool
    matches_played: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0


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


@dataclass(frozen=True)
class _ResolvedAuthenticatedDbAgent:
    context: AuthenticatedAgentContext
    api_key_id: str
    user_id: str
    elo_rating: int
    key_hash: str


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

        alliances_by_match = _load_persisted_alliances_by_match(
            matches=matches,
            alliance_rows=alliance_rows,
            player_rows=player_rows,
        )
        agent_profiles_by_match = _load_agent_profiles_by_match(
            matches=matches,
            player_rows=player_rows,
            api_key_rows=api_key_rows,
        )
        authenticated_keys_by_match = _load_authenticated_agent_keys_by_match(
            matches=matches,
            player_rows=player_rows,
            api_key_rows=api_key_rows,
        )
        joined_agents_by_match = _load_joined_agents_by_match(
            matches=matches,
            player_rows=player_rows,
            api_key_rows=api_key_rows,
        )
        joined_humans_by_match = _load_joined_humans_by_match(
            matches=matches,
            player_rows=player_rows,
        )
        public_competitor_kinds_by_match = _load_public_competitor_kinds_by_match(
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


def persist_advanced_match_tick(*, database_url: str, advanced_tick: AdvancedMatchTick) -> None:
    engine = create_engine(database_url)
    with Session(engine) as session, session.begin():
        match = session.get(Match, advanced_tick.match_id)
        if match is None:
            raise KeyError(f"Match '{advanced_tick.match_id}' was not found.")

        match.current_tick = advanced_tick.resolved_tick
        match.state = advanced_tick.next_state.model_dump(mode="json")
        session.add(
            TickLog(
                match_id=advanced_tick.match_id,
                tick=advanced_tick.resolved_tick,
                state_snapshot=advanced_tick.next_state.model_dump(mode="json"),
                orders=advanced_tick.accepted_orders.model_dump(mode="json"),
                events=[event.model_dump(mode="json") for event in advanced_tick.events],
            )
        )


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
            authenticated_agent_resolution = _resolve_authenticated_agent_from_db_key_hash(
                session=session,
                key_hash=authenticated_api_key_hash,
            )
            if authenticated_agent_resolution is None:
                raise MatchLobbyCreationError(
                    code="invalid_api_key",
                    message="A valid active X-API-Key header is required.",
                )
            resolved_authenticated_agent = authenticated_agent_resolution.context
            creator_api_key_id = authenticated_agent_resolution.api_key_id
            creator_user_id = authenticated_agent_resolution.user_id
            creator_elo_rating = authenticated_agent_resolution.elo_rating
            creator_display_name = authenticated_agent_resolution.context.display_name
            creator_is_agent = True
        elif authenticated_human_user_id is not None:
            creator_user_id = authenticated_human_user_id
            creator_display_name = _resolve_human_display_name(
                session=session,
                user_id=authenticated_human_user_id,
            )
            creator_elo_rating = _resolve_human_elo_rating(
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
                id=_build_match_scoped_player_id(match_id=match_id, join_index=1),
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

        joined_record = _load_match_record_from_session(session=session, match=match)
        assigned_player_id = (
            joined_record.joinable_player_ids[0] if joined_record.joinable_player_ids else None
        )

        if authenticated_api_key_hash is not None:
            authenticated_agent_resolution = _resolve_authenticated_agent_from_db_key_hash(
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

            if assigned_player_id is None:
                raise MatchJoinError(
                    code="match_not_joinable",
                    message=f"Match '{match_id}' does not support agent joins.",
                )

            session.add(
                Player(
                    id=_build_match_scoped_player_id(
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
            updated_record = _load_match_record_from_session(session=session, match=match)
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
                    agent_id=_build_human_actor_id(authenticated_human_user_id),
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
                id=_build_match_scoped_player_id(
                    match_id=match_id,
                    join_index=len(joined_record.joined_agents)
                    + len(joined_record.joined_humans)
                    + 1,
                ),
                user_id=authenticated_human_user_id,
                match_id=match_id,
                display_name=_resolve_human_display_name(
                    session=session,
                    user_id=authenticated_human_user_id,
                ),
                is_agent=False,
                api_key_id=None,
                elo_rating=_resolve_human_elo_rating(
                    session=session,
                    user_id=authenticated_human_user_id,
                ),
                alliance_id=None,
                alliance_joined_tick=None,
                eliminated_at=None,
            )
        )
        updated_record = _load_match_record_from_session(session=session, match=match)

    return JoinedMatch(
        response=MatchJoinResponse(
            status="accepted",
            match_id=match_id,
            agent_id=_build_human_actor_id(authenticated_human_user_id),
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
        authenticated_agent_resolution: _ResolvedAuthenticatedDbAgent | None = None
        if authenticated_api_key_hash is not None:
            authenticated_agent_resolution = _resolve_authenticated_agent_from_db_key_hash(
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
        started_record = _load_match_record_from_session(session=session, match=match)

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


def _load_match_record_from_session(*, session: Session, match: Match) -> MatchRecord:
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
    joined_agents = _load_joined_agents_by_match(
        matches=[match],
        player_rows=player_rows,
        api_key_rows=api_key_rows,
    ).get(match_id, {})
    joined_humans = _load_joined_humans_by_match(
        matches=[match],
        player_rows=player_rows,
    ).get(match_id, {})
    agent_profiles = _load_agent_profiles_by_match(
        matches=[match],
        player_rows=player_rows,
        api_key_rows=api_key_rows,
    ).get(match_id, [])
    authenticated_agent_keys = _load_authenticated_agent_keys_by_match(
        matches=[match],
        player_rows=player_rows,
        api_key_rows=api_key_rows,
    ).get(match_id, [])
    public_competitor_kinds = _load_public_competitor_kinds_by_match(
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


def get_match_history(*, database_url: str, match_id: str) -> MatchHistoryResponse:
    engine = create_engine(database_url)
    with Session(engine) as session:
        match = session.get(Match, match_id)
        if match is None:
            raise MatchHistoryNotFoundError(match_id)

        ticks = (
            session.execute(
                select(TickLog.tick)
                .where(TickLog.match_id == match_id)
                .order_by(TickLog.tick, TickLog.id)
            )
            .scalars()
            .all()
        )

    return MatchHistoryResponse(
        match_id=str(match.id),
        status=MatchStatus(match.status),
        current_tick=int(match.current_tick),
        tick_interval_seconds=int(match.config.get("turn_seconds", 0)),
        history=[MatchHistoryEntry(tick=int(tick)) for tick in ticks],
    )


def get_match_replay_tick(
    *, database_url: str, match_id: str, tick: int
) -> MatchReplayTickResponse:
    engine = create_engine(database_url)
    with Session(engine) as session:
        match = session.get(Match, match_id)
        if match is None:
            raise MatchHistoryNotFoundError(match_id)

        tick_row = session.scalar(
            select(TickLog)
            .where(TickLog.match_id == match_id, TickLog.tick == tick)
            .order_by(TickLog.id)
        )
        if tick_row is None:
            raise TickHistoryNotFoundError((match_id, tick))

    return MatchReplayTickResponse(
        match_id=str(match.id),
        tick=int(tick_row.tick),
        state_snapshot=tick_row.state_snapshot,
        orders=tick_row.orders,
        events=tick_row.events,
    )


def get_public_leaderboard(*, database_url: str) -> PublicLeaderboardResponse:
    engine = create_engine(database_url)
    with Session(engine) as session:
        completed_matches = session.scalars(
            select(Match)
            .where(Match.status == MatchStatus.COMPLETED.value)
            .order_by(Match.updated_at.desc(), Match.id.desc())
        ).all()
        if not completed_matches:
            return PublicLeaderboardResponse()

        match_ids = [match.id for match in completed_matches]
        players = session.scalars(
            select(Player)
            .where(Player.match_id.in_(match_ids))
            .order_by(Player.match_id, Player.id)
        ).all()

    players_by_match: dict[str, list[Player]] = defaultdict(list)
    for player in players:
        players_by_match[str(player.match_id)].append(player)

    ranked_matches = sorted(
        completed_matches,
        key=lambda match: (
            -_to_utc(match.updated_at).timestamp(),
            str(match.id),
        ),
    )
    aggregates: dict[str, _LeaderboardAggregate] = {}
    for match in ranked_matches:
        winner_alliance_id = (
            str(match.winner_alliance) if match.winner_alliance is not None else None
        )
        for player in players_by_match.get(str(match.id), []):
            competitor_kind: Literal["human", "agent"] = "agent" if player.is_agent else "human"
            competitor_identity = _leaderboard_competitor_identity(player)
            aggregate = aggregates.get(competitor_identity)
            if aggregate is None:
                aggregate = _LeaderboardAggregate(
                    competitor_key=competitor_identity,
                    display_name=player.display_name,
                    competitor_kind=competitor_kind,
                    elo=int(player.elo_rating),
                    provisional=True,
                )
                aggregates[competitor_identity] = aggregate

            aggregate.matches_played += 1
            player_alliance_id = str(player.alliance_id) if player.alliance_id is not None else None
            if winner_alliance_id is None:
                aggregate.draws += 1
            elif player_alliance_id == winner_alliance_id:
                aggregate.wins += 1
            else:
                aggregate.losses += 1

    ordered_aggregates = sorted(
        aggregates.values(),
        key=lambda aggregate: (
            -aggregate.elo,
            aggregate.display_name.casefold(),
            aggregate.competitor_kind,
            aggregate.competitor_key,
        ),
    )
    return PublicLeaderboardResponse(
        leaderboard=[
            LeaderboardEntry(
                rank=index,
                display_name=aggregate.display_name,
                competitor_kind=aggregate.competitor_kind,
                elo=aggregate.elo,
                provisional=aggregate.provisional,
                matches_played=aggregate.matches_played,
                wins=aggregate.wins,
                losses=aggregate.losses,
                draws=aggregate.draws,
            )
            for index, aggregate in enumerate(ordered_aggregates, start=1)
        ]
    )


def get_public_match_summaries(*, database_url: str) -> MatchListResponse:
    engine = create_engine(database_url)
    with Session(engine) as session:
        public_matches = session.scalars(
            select(Match).where(Match.status != MatchStatus.COMPLETED.value).order_by(Match.id)
        ).all()
        if not public_matches:
            return MatchListResponse()

        match_ids = [match.id for match in public_matches]
        players = session.scalars(
            select(Player)
            .where(Player.match_id.in_(match_ids))
            .order_by(Player.match_id, Player.id)
        ).all()

    player_counts_by_match: dict[str, int] = defaultdict(int)
    for player in players:
        player_counts_by_match[str(player.match_id)] += 1

    return MatchListResponse(
        matches=[
            MatchSummary(
                match_id=str(match.id),
                status=MatchStatus(match.status),
                map=str(match.config.get("map", "")),
                tick=int(match.current_tick),
                tick_interval_seconds=int(match.config.get("turn_seconds", 0)),
                current_player_count=player_counts_by_match.get(str(match.id), 0),
                max_player_count=max(int(match.config.get("max_players", 0)), 0),
                open_slot_count=max(
                    int(match.config.get("max_players", 0))
                    - player_counts_by_match.get(str(match.id), 0),
                    0,
                ),
            )
            for match in sorted(public_matches, key=_public_match_browse_sort_key)
        ]
    )


def get_public_match_detail(*, database_url: str, match_id: str) -> PublicMatchDetailResponse:
    engine = create_engine(database_url)
    with Session(engine) as session:
        match = session.scalar(
            select(Match).where(
                Match.id == match_id,
                Match.status != MatchStatus.COMPLETED.value,
            )
        )
        if match is None:
            raise PublicMatchDetailNotFoundError(match_id)

        state = MatchState.model_validate(match.state)
        players = session.scalars(
            select(Player)
            .where(Player.match_id == match.id)
            .order_by(Player.display_name, Player.is_agent, Player.id)
        ).all()
        persisted_player_mapping = _build_persisted_player_mapping(
            canonical_player_ids=sorted(state.players),
            persisted_players=players,
        )

    return PublicMatchDetailResponse(
        match_id=str(match.id),
        status=MatchStatus(match.status),
        map=str(match.config.get("map", "")),
        tick=int(match.current_tick),
        tick_interval_seconds=int(match.config.get("turn_seconds", 0)),
        current_player_count=len(players),
        max_player_count=max(int(match.config.get("max_players", 0)), 0),
        open_slot_count=max(int(match.config.get("max_players", 0)) - len(players), 0),
        roster=[
            PublicMatchRosterRow(
                player_id=canonical_player_id,
                display_name=player.display_name,
                competitor_kind="agent" if player.is_agent else "human",
            )
            for player in sorted(players, key=_public_match_roster_sort_key)
            if (canonical_player_id := persisted_player_mapping.get(str(player.id))) is not None
        ],
    )


def _leaderboard_competitor_identity(player: Player) -> str:
    if player.is_agent:
        if player.api_key_id is not None:
            return f"agent:{player.api_key_id}"
        return f"agent-user:{player.user_id}"
    return f"human:{player.user_id}"


def _public_match_browse_sort_key(match: Match) -> tuple[int, float, int, str]:
    return (
        _public_status_priority(MatchStatus(match.status)),
        -_to_utc(match.updated_at).timestamp(),
        -int(match.current_tick),
        str(match.id),
    )


def _public_match_roster_sort_key(player: Player) -> tuple[str, int, str, str]:
    return (
        player.display_name.casefold(),
        0 if not player.is_agent else 1,
        player.display_name,
        str(player.id),
    )


def _public_status_priority(status: MatchStatus) -> int:
    if status is MatchStatus.LOBBY:
        return 0
    if status is MatchStatus.ACTIVE:
        return 1
    if status is MatchStatus.PAUSED:
        return 2
    return 3


def get_completed_match_summaries(*, database_url: str) -> CompletedMatchSummaryListResponse:
    engine = create_engine(database_url)
    with Session(engine) as session:
        completed_matches = session.scalars(
            select(Match)
            .where(Match.status == MatchStatus.COMPLETED.value)
            .order_by(Match.updated_at.desc(), Match.current_tick.desc(), Match.id)
        ).all()
        if not completed_matches:
            return CompletedMatchSummaryListResponse()

        match_ids = [match.id for match in completed_matches]
        players = session.scalars(
            select(Player)
            .where(Player.match_id.in_(match_ids))
            .order_by(Player.match_id, Player.display_name, Player.id)
        ).all()
        alliances = session.scalars(
            select(Alliance)
            .where(Alliance.match_id.in_(match_ids))
            .order_by(Alliance.match_id, Alliance.id)
        ).all()

    players_by_match: dict[str, list[Player]] = defaultdict(list)
    players_by_match_and_alliance: dict[tuple[str, str], list[Player]] = defaultdict(list)
    for player in players:
        match_id = str(player.match_id)
        players_by_match[match_id].append(player)
        if player.alliance_id is not None:
            players_by_match_and_alliance[(match_id, str(player.alliance_id))].append(player)

    alliances_by_match_and_id = {
        (str(alliance.match_id), str(alliance.id)): alliance for alliance in alliances
    }
    summaries = [
        CompletedMatchSummary(
            match_id=str(match.id),
            map=str(match.config.get("map", "")),
            final_tick=int(match.current_tick),
            tick_interval_seconds=int(match.config.get("turn_seconds", 0)),
            player_count=len(players_by_match.get(str(match.id), [])),
            completed_at=_to_utc(match.updated_at),
            winning_alliance_name=_winning_alliance_name(
                match=match,
                alliances_by_match_and_id=alliances_by_match_and_id,
            ),
            winning_player_display_names=_winning_player_display_names(
                match=match,
                players_by_match_and_alliance=players_by_match_and_alliance,
            ),
        )
        for match in completed_matches
    ]
    return CompletedMatchSummaryListResponse(matches=summaries)


def _load_persisted_alliances_by_match(
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
        derived_registry = InMemoryMatchRegistry()
        derived_alliances = derived_registry._derive_alliances_from_state(state)  # noqa: SLF001
        persisted_player_mapping = _build_persisted_player_mapping(
            canonical_player_ids=sorted(state.players),
            persisted_players=players_by_match.get(match_id, []),
        )
        persisted_rows_for_match = [
            alliance_row for alliance_row in alliance_rows if str(alliance_row.match_id) == match_id
        ]
        persisted_alliances = _merge_persisted_alliance_metadata(
            derived_alliances=derived_alliances,
            persisted_rows=persisted_rows_for_match,
            players_by_match_and_alliance=players_by_match_and_alliance,
            persisted_player_mapping=persisted_player_mapping,
            match_id=match_id,
        )
        if persisted_alliances:
            alliances_by_match[match_id] = persisted_alliances

    return alliances_by_match


def _load_agent_profiles_by_match(
    *,
    matches: Sequence[Match],
    player_rows: Sequence[Player],
    api_key_rows: Sequence[ApiKey],
) -> dict[str, list[AgentProfileResponse]]:
    players_by_match: dict[str, list[Player]] = defaultdict(list)
    api_keys_by_id = {str(api_key.id): api_key for api_key in api_key_rows}
    seeded_profiles_by_key_hash = {
        hash_api_key(build_seeded_agent_api_key(profile.agent_id)): profile
        for profile in build_seeded_agent_profiles()
    }
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
            agent_identity = _resolve_loaded_agent_identity(
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


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _winning_alliance_name(
    *,
    match: Match,
    alliances_by_match_and_id: dict[tuple[str, str], Alliance],
) -> str | None:
    if match.winner_alliance is None:
        return None
    alliance = alliances_by_match_and_id.get((str(match.id), str(match.winner_alliance)))
    return alliance.name if alliance is not None else None


def _winning_player_display_names(
    *,
    match: Match,
    players_by_match_and_alliance: dict[tuple[str, str], list[Player]],
) -> list[str]:
    if match.winner_alliance is None:
        return []
    winners = players_by_match_and_alliance.get((str(match.id), str(match.winner_alliance)), [])
    return sorted(player.display_name for player in winners)


def _load_authenticated_agent_keys_by_match(
    *,
    matches: Sequence[Match],
    player_rows: Sequence[Player],
    api_key_rows: Sequence[ApiKey],
) -> dict[str, list[AuthenticatedAgentKeyRecord]]:
    players_by_match: dict[str, list[Player]] = defaultdict(list)
    api_keys_by_id = {str(api_key.id): api_key for api_key in api_key_rows}
    seeded_profiles_by_key_hash = {
        hash_api_key(build_seeded_agent_api_key(profile.agent_id)): profile
        for profile in build_seeded_agent_profiles()
    }
    for player in player_rows:
        players_by_match[str(player.match_id)].append(player)

    authenticated_keys_by_match: dict[str, list[AuthenticatedAgentKeyRecord]] = {}
    for match in matches:
        match_id = str(match.id)
        state = MatchState.model_validate(match.state)
        persisted_player_mapping = _build_persisted_player_mapping(
            canonical_player_ids=sorted(state.players),
            persisted_players=players_by_match.get(match_id, []),
        )
        authenticated_keys = [
            AuthenticatedAgentKeyRecord(
                agent_id=_resolve_loaded_agent_identity(
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


def _load_joined_agents_by_match(
    *,
    matches: Sequence[Match],
    player_rows: Sequence[Player],
    api_key_rows: Sequence[ApiKey],
) -> dict[str, dict[str, str]]:
    players_by_match: dict[str, list[Player]] = defaultdict(list)
    api_keys_by_id = {str(api_key.id): api_key for api_key in api_key_rows}
    seeded_profiles_by_key_hash = {
        hash_api_key(build_seeded_agent_api_key(profile.agent_id)): profile
        for profile in build_seeded_agent_profiles()
    }
    for player in player_rows:
        players_by_match[str(player.match_id)].append(player)

    joined_agents_by_match: dict[str, dict[str, str]] = {}
    for match in matches:
        match_id = str(match.id)
        state = MatchState.model_validate(match.state)
        persisted_player_mapping = _build_persisted_player_mapping(
            canonical_player_ids=sorted(state.players),
            persisted_players=players_by_match.get(match_id, []),
        )
        joined_agents = {
            _resolve_loaded_agent_identity(
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


def _load_joined_humans_by_match(
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
        persisted_player_mapping = _build_persisted_player_mapping(
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


def _load_public_competitor_kinds_by_match(
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
        persisted_player_mapping = _build_persisted_player_mapping(
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


def _build_persisted_player_mapping(
    *,
    canonical_player_ids: list[str],
    persisted_players: Sequence[Player],
) -> dict[str, str]:
    canonical_player_id_set = set(canonical_player_ids)
    persisted_player_mapping: dict[str, str] = {}
    seen_canonical_player_ids: set[str] = set()
    for player in persisted_players:
        canonical_player_id = _canonical_player_id_from_persisted_player_id(
            persisted_player_id=str(player.id),
            canonical_player_ids=canonical_player_id_set,
        )
        if canonical_player_id is None:
            continue
        if canonical_player_id in seen_canonical_player_ids:
            return {}
        persisted_player_mapping[str(player.id)] = canonical_player_id
        seen_canonical_player_ids.add(canonical_player_id)

    return persisted_player_mapping


def _canonical_player_id_from_persisted_player_id(
    *, persisted_player_id: str, canonical_player_ids: set[str]
) -> str | None:
    persisted_segments = persisted_player_id.split("-")
    if len(persisted_segments) != 5:
        return None
    try:
        join_index = int(persisted_segments[-1], 16)
    except ValueError:
        return None

    canonical_player_id = f"player-{join_index}"
    if canonical_player_id not in canonical_player_ids:
        return None
    return canonical_player_id


def _build_joined_player_id(join_index: int) -> str:
    return f"ffffffff-ffff-ffff-ffff-{join_index:012x}"


def _build_match_scoped_player_id(*, match_id: str, join_index: int) -> str:
    cleaned_match_id = match_id.replace("-", "")
    match_prefix = (cleaned_match_id[:16] + cleaned_match_id[-4:]).ljust(20, "f")
    return (
        f"{match_prefix[:8]}-"
        f"{match_prefix[8:12]}-"
        f"{match_prefix[12:16]}-"
        f"{match_prefix[16:20]}-"
        f"{join_index:012x}"
    )


def _build_human_actor_id(user_id: str) -> str:
    return f"human:{user_id}"


def _resolve_human_display_name(*, session: Session, user_id: str) -> str:
    existing_player = session.scalar(
        select(Player)
        .where(Player.user_id == user_id)
        .order_by(Player.is_agent.asc(), Player.id.asc())
    )
    if existing_player is not None:
        return existing_player.display_name
    return user_id


def _resolve_human_elo_rating(*, session: Session, user_id: str) -> int:
    existing_player = session.scalar(
        select(Player)
        .where(Player.user_id == user_id)
        .order_by(Player.is_agent.asc(), Player.id.asc())
    )
    if existing_player is not None:
        return int(existing_player.elo_rating)
    return 0


@dataclass(frozen=True)
class _LoadedAgentIdentity:
    agent_id: str
    is_seeded: bool


def resolve_authenticated_agent_context_from_db(
    *, database_url: str, api_key: str
) -> AuthenticatedAgentContext | None:
    engine = create_engine(database_url)
    with Session(engine) as session:
        resolved = _resolve_authenticated_agent_from_db_key_hash(
            session=session,
            key_hash=hash_api_key(api_key),
        )
    return resolved.context if resolved is not None else None


def resolve_human_player_id_from_db(
    *, database_url: str, match_id: str, user_id: str
) -> str | None:
    engine = create_engine(database_url)
    with Session(engine) as session:
        match = session.get(Match, match_id)
        if match is None:
            return None

        persisted_players = session.scalars(
            select(Player).where(Player.match_id == match_id).order_by(Player.id)
        ).all()
        state = MatchState.model_validate(match.state)
        persisted_player_mapping = _build_persisted_player_mapping(
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


def _resolve_loaded_agent_identity(
    *,
    player: Player,
    api_key: ApiKey | None,
    seeded_profiles_by_key_hash: dict[str, AgentProfileResponse],
) -> _LoadedAgentIdentity:
    seeded_profile = (
        seeded_profiles_by_key_hash.get(api_key.key_hash) if api_key is not None else None
    )
    if seeded_profile is not None:
        return _LoadedAgentIdentity(agent_id=seeded_profile.agent_id, is_seeded=True)
    return _LoadedAgentIdentity(
        agent_id=_build_non_seeded_agent_id(str(api_key.id))
        if api_key is not None
        else f"agent-{player.display_name.casefold()}",
        is_seeded=False,
    )


def _resolve_authenticated_agent_from_db_key_hash(
    *, session: Session, key_hash: str
) -> _ResolvedAuthenticatedDbAgent | None:
    api_key = session.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash))
    if api_key is None or not api_key.is_active:
        return None

    persisted_players = session.scalars(
        select(Player).where(Player.api_key_id == api_key.id).order_by(Player.match_id, Player.id)
    ).all()
    existing_agent_player = next((player for player in persisted_players if player.is_agent), None)
    if persisted_players and existing_agent_player is None:
        return None

    seeded_profile = _build_seeded_profiles_by_key_hash().get(api_key.key_hash)
    if seeded_profile is not None:
        return _ResolvedAuthenticatedDbAgent(
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

    return _ResolvedAuthenticatedDbAgent(
        context=AuthenticatedAgentContext(
            agent_id=_build_non_seeded_agent_id(str(api_key.id)),
            display_name=(
                existing_agent_player.display_name
                if existing_agent_player is not None
                else _build_non_seeded_display_name(str(api_key.id))
            ),
            is_seeded=False,
        ),
        api_key_id=str(api_key.id),
        user_id=str(api_key.user_id),
        elo_rating=int(api_key.elo_rating),
        key_hash=api_key.key_hash,
    )


def _build_seeded_profiles_by_key_hash() -> dict[str, AgentProfileResponse]:
    return {
        hash_api_key(build_seeded_agent_api_key(profile.agent_id)): profile
        for profile in build_seeded_agent_profiles()
    }


def _build_non_seeded_agent_id(api_key_id: str) -> str:
    return f"agent-api-key-{api_key_id}"


def _build_non_seeded_display_name(api_key_id: str) -> str:
    return f"Agent {api_key_id[:8]}"


def _merge_persisted_alliance_metadata(
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
