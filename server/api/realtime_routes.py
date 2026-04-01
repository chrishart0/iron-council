from __future__ import annotations

from collections.abc import Awaitable, Callable
from http import HTTPStatus
from typing import cast

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect

from server.agent_registry import InMemoryMatchRegistry
from server.models.realtime import RealtimeViewerRole
from server.settings import Settings
from server.websocket import MatchWebSocketManager, build_match_realtime_envelope

from .errors import ApiError

ResolveWebsocketPlayerViewer = Callable[..., str]
WebsocketErrorHandler = Callable[[WebSocket, ApiError], Awaitable[None]]


def register_realtime_routes(
    app: FastAPI,
    *,
    registry: InMemoryMatchRegistry,
    websocket_manager: MatchWebSocketManager,
    settings: Settings,
    history_database_url: str | None,
    resolve_websocket_player_viewer: ResolveWebsocketPlayerViewer,
    send_websocket_auth_error: WebsocketErrorHandler,
    close_websocket_for_api_error: WebsocketErrorHandler,
) -> None:
    async def _handle_match_websocket(
        websocket: WebSocket,
        match_id: str,
        viewer: str = Query(default="spectator"),
        player_id: str | None = Query(default=None),
        token: str | None = Query(default=None),
    ) -> None:
        record = registry.get_match(match_id)
        if record is None:
            await websocket.close(code=1008, reason="match_not_found")
            return

        try:
            if viewer not in {"player", "spectator"}:
                raise ApiError(
                    status_code=HTTPStatus.BAD_REQUEST,
                    code="invalid_viewer",
                    message="Websocket viewer must be either 'player' or 'spectator'.",
                )
            viewer_role = cast(RealtimeViewerRole, viewer)
            resolved_player_id = (
                resolve_websocket_player_viewer(
                    registry=registry,
                    settings=settings,
                    history_database_url=history_database_url,
                    match_id=match_id,
                    player_id=player_id,
                    token=token,
                )
                if viewer_role == "player"
                else None
            )
        except ApiError as exc:
            if exc.code in {"invalid_websocket_auth", "player_auth_mismatch"}:
                await send_websocket_auth_error(websocket, exc)
                return
            await close_websocket_for_api_error(websocket, exc)
            return

        await websocket.accept()
        try:
            await websocket.send_json(
                build_match_realtime_envelope(
                    registry=registry,
                    match_id=match_id,
                    viewer_role=viewer_role,
                    player_id=resolved_player_id,
                ).model_dump(mode="json")
            )
            websocket_manager.register(
                match_id=match_id,
                websocket=websocket,
                viewer_role=viewer_role,
                player_id=resolved_player_id,
            )
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            websocket_manager.unregister(match_id=match_id, websocket=websocket)

    @app.websocket("/ws/match/{match_id}")
    async def match_websocket(
        websocket: WebSocket,
        match_id: str,
        viewer: str = Query(default="spectator"),
        player_id: str | None = Query(default=None),
        token: str | None = Query(default=None),
    ) -> None:
        await _handle_match_websocket(
            websocket=websocket,
            match_id=match_id,
            viewer=viewer,
            player_id=player_id,
            token=token,
        )

    @app.websocket("/ws/matches/{match_id}")
    async def legacy_match_websocket(
        websocket: WebSocket,
        match_id: str,
        viewer: str = Query(default="spectator"),
        player_id: str | None = Query(default=None),
        token: str | None = Query(default=None),
    ) -> None:
        await _handle_match_websocket(
            websocket=websocket,
            match_id=match_id,
            viewer=viewer,
            player_id=player_id,
            token=token,
        )
