from __future__ import annotations

import os
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Final, cast

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketState

from server import __version__
from server.agent_registry import AdvancedMatchTick, InMemoryMatchRegistry, MatchRecord
from server.api import (
    AppServices,
    build_authenticated_access_router,
    build_authenticated_match_router,
    build_public_api_router,
    register_error_handlers,
    register_public_metadata_routes,
    register_realtime_routes,
)
from server.api.errors import ApiError
from server.db.registry import load_match_registry_from_database, persist_advanced_match_tick
from server.models.api import ApiErrorDetail, ApiErrorResponse, PublicMatchRosterRow
from server.models.domain import MatchStatus
from server.runtime import MatchRuntime
from server.settings import Settings, get_settings
from server.websocket import MatchWebSocketManager, broadcast_match_update


def get_match_registry(request: Request) -> InMemoryMatchRegistry:
    return request.app.state.match_registry  # type: ignore[no-any-return]


TickPersistence = Callable[[AdvancedMatchTick], None]
_DEFAULT_TICK_PERSISTENCE: Final = object()


def _public_match_status_priority(status: MatchStatus) -> int:
    if status is MatchStatus.LOBBY:
        return 0
    if status is MatchStatus.ACTIVE:
        return 1
    if status is MatchStatus.PAUSED:
        return 2
    return 3


async def _close_websocket_for_api_error(websocket: WebSocket, exc: ApiError) -> None:
    if websocket.client_state is WebSocketState.CONNECTED:
        await websocket.close(code=1008, reason=exc.code)
        return
    await websocket.close(code=1008, reason=exc.code)


async def _send_websocket_auth_error(websocket: WebSocket, exc: ApiError) -> None:
    if websocket.client_state is not WebSocketState.CONNECTED:
        await websocket.accept()
    payload = ApiErrorResponse(error=ApiErrorDetail(code=exc.code, message=exc.message))
    await websocket.send_json(payload.model_dump(mode="json"))
    await websocket.close(code=1008, reason=exc.code)


def create_app(
    *,
    match_registry: InMemoryMatchRegistry | None = None,
    tick_persistence: TickPersistence | None | object = _DEFAULT_TICK_PERSISTENCE,
    settings_override: dict[str, str] | None = None,
) -> FastAPI:
    settings_env = dict(os.environ)
    if settings_override is not None:
        settings_env.update(settings_override)
    settings = get_settings(env=settings_env)
    registry = match_registry or _load_default_match_registry(settings=settings)
    websocket_manager = MatchWebSocketManager()
    runtime_tick_persistence = (
        _load_runtime_tick_persistence(settings=settings, match_registry=match_registry)
        if tick_persistence is _DEFAULT_TICK_PERSISTENCE
        else cast(TickPersistence | None, tick_persistence)
    )
    history_database_url = _load_history_database_url(settings=settings)
    app_services = AppServices(
        settings=settings,
        history_database_url=history_database_url,
    )

    async def broadcast_current_match(match_id: str) -> None:
        await broadcast_match_update(
            registry=registry,
            manager=websocket_manager,
            match_id=match_id,
        )

    async def broadcast_advanced_tick(advanced_tick: AdvancedMatchTick) -> None:
        await broadcast_current_match(advanced_tick.match_id)

    match_runtime = MatchRuntime(
        registry,
        tick_persistence=runtime_tick_persistence,
        tick_broadcast=broadcast_advanced_tick,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
        app.state.match_registry = registry
        app.state.match_websocket_manager = websocket_manager
        app.state.match_runtime = match_runtime
        app.state.settings = settings
        app.state.history_database_url = history_database_url
        await match_runtime.start()
        try:
            yield
        finally:
            await match_runtime.stop()

    app = FastAPI(title="iron-council-server", version=__version__, lifespan=lifespan)
    app.state.match_registry = registry
    app.state.match_websocket_manager = websocket_manager
    app.state.match_runtime = match_runtime
    app.state.settings = settings
    app.state.history_database_url = history_database_url
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_browser_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)
    register_public_metadata_routes(app)
    register_realtime_routes(
        app,
        registry=registry,
        websocket_manager=websocket_manager,
        app_services=app_services,
        send_websocket_auth_error=_send_websocket_auth_error,
        close_websocket_for_api_error=_close_websocket_for_api_error,
    )
    app.include_router(
        build_public_api_router(
            match_registry_provider=get_match_registry,
            history_database_url=history_database_url,
            public_match_status_priority=_public_match_status_priority,
            build_in_memory_public_match_roster=(
                lambda registry, record: _build_in_memory_public_match_roster(
                    registry=registry,
                    record=record,
                )
            ),
        )
    )
    app.include_router(
        build_authenticated_access_router(
            match_registry_provider=get_match_registry,
            app_services=app_services,
            ensure_match_running=match_runtime.ensure_match_running,
        )
    )
    app.include_router(
        build_authenticated_match_router(
            match_registry_provider=get_match_registry,
            app_services=app_services,
            broadcast_current_match=broadcast_current_match,
        )
    )
    return app


def _load_default_match_registry(*, settings: Settings) -> InMemoryMatchRegistry:
    if settings.match_registry_backend == "memory":
        return InMemoryMatchRegistry()
    if settings.match_registry_backend == "db":
        return load_match_registry_from_database(settings.database_url)
    raise ValueError(
        "Unsupported "
        f"IRON_COUNCIL_MATCH_REGISTRY_BACKEND value {settings.match_registry_backend!r}; "
        "expected 'memory' or 'db'."
    )


def _load_runtime_tick_persistence(
    *,
    settings: Settings,
    match_registry: InMemoryMatchRegistry | None,
) -> Callable[[AdvancedMatchTick], None] | None:
    if match_registry is not None:
        return None

    if settings.match_registry_backend != "db":
        return None

    database_url = settings.database_url

    def persist_tick(advanced_tick: AdvancedMatchTick) -> None:
        persist_advanced_match_tick(database_url=database_url, advanced_tick=advanced_tick)

    return persist_tick


def _load_history_database_url(*, settings: Settings) -> str | None:
    if settings.match_registry_backend != "db":
        return None
    return settings.database_url


def _build_in_memory_public_match_roster(
    *, registry: InMemoryMatchRegistry, record: MatchRecord
) -> list[PublicMatchRosterRow]:
    visible_player_ids = [
        player_id
        for player_id, player_state in sorted(record.state.players.items())
        if player_state.cities_owned and not player_state.is_eliminated
    ]
    joined_human_player_ids = sorted(set(record.joined_humans.values()))
    joined_agent_player_ids = sorted(
        {
            player_id
            for agent_id, player_id in record.joined_agents.items()
            if agent_id.startswith("agent-")
        }
    )

    if (
        joined_human_player_ids
        and len(joined_human_player_ids) == record.public_current_player_count
    ):
        roster_player_ids = joined_human_player_ids
    else:
        joined_player_ids = sorted(set(joined_human_player_ids) | set(joined_agent_player_ids))
        roster_player_ids = joined_player_ids or visible_player_ids

    if not roster_player_ids:
        roster_player_ids = visible_player_ids

    human_player_ids = set(joined_human_player_ids)
    roster = [
        PublicMatchRosterRow(
            player_id=player_id,
            display_name=profile.display_name,
            competitor_kind=record.public_competitor_kinds.get(
                player_id,
                "human" if player_id in human_player_ids else "agent",
            ),
        )
        for player_id in roster_player_ids
        if (profile := registry.get_agent_profile(f"agent-{player_id}")) is not None
    ]
    ordered_roster = sorted(
        roster,
        key=lambda row: (
            row.display_name.casefold(),
            0 if row.competitor_kind == "human" else 1,
            row.display_name,
        ),
    )
    return ordered_roster[: record.public_current_player_count]


app = create_app()
