from __future__ import annotations

from collections.abc import Awaitable, Callable
from http import HTTPStatus
from typing import Any

from fastapi import APIRouter, Depends

from server.agent_registry import InMemoryMatchRegistry
from server.auth import hash_api_key
from server.db.registry import (
    MatchLobbyCreationError,
    MatchLobbyStartError,
    create_match_lobby,
    start_match_lobby,
)
from server.models.api import (
    MatchLobbyCreateRequest,
    MatchLobbyCreateResponse,
    MatchLobbyStartResponse,
)

from .app_services import ApiKeyHeader, AppServices, AuthorizationHeader
from .errors import API_ERROR_RESPONSE_SCHEMA, ApiError

RegistryProvider = Callable[..., InMemoryMatchRegistry]
EnsureMatchRunning = Callable[[str], Awaitable[None]]


def _authenticated_lobby_route_responses(
    *status_codes: HTTPStatus,
) -> dict[int | str, dict[str, Any]]:
    return {
        int(HTTPStatus.UNAUTHORIZED): API_ERROR_RESPONSE_SCHEMA,
        **{int(status_code): API_ERROR_RESPONSE_SCHEMA for status_code in status_codes},
    }


def build_authenticated_lobby_router(
    *,
    match_registry_provider: RegistryProvider,
    app_services: AppServices,
    ensure_match_running: EnsureMatchRunning,
) -> APIRouter:
    router = APIRouter()
    registry_dependency = Depends(match_registry_provider)
    history_database_url = app_services.history_database_url

    @router.post(
        "/matches",
        response_model=MatchLobbyCreateResponse,
        status_code=HTTPStatus.CREATED,
        responses=_authenticated_lobby_route_responses(
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.SERVICE_UNAVAILABLE,
        ),
    )
    async def create_match_lobby_route(
        create_request: MatchLobbyCreateRequest,
        registry: InMemoryMatchRegistry = registry_dependency,
        api_key: ApiKeyHeader = None,
        authorization: AuthorizationHeader = None,
    ) -> MatchLobbyCreateResponse:
        if history_database_url is None and api_key is None and authorization is None:
            raise ApiError(
                status_code=HTTPStatus.UNAUTHORIZED,
                code="invalid_api_key",
                message="A valid active X-API-Key header is required.",
            )
        authenticated_actor = app_services.resolve_authenticated_lobby_actor(
            registry=registry,
            api_key=api_key,
            authorization=authorization,
        )
        if history_database_url is None:
            raise ApiError(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                code="match_lobby_creation_unavailable",
                message="Authenticated match lobby creation is only available in DB-backed mode.",
            )
        try:
            created_lobby = create_match_lobby(
                database_url=history_database_url,
                authenticated_agent_id=(
                    authenticated_actor.agent.agent_id
                    if authenticated_actor.agent is not None
                    else None
                ),
                authenticated_agent_display_name=(
                    authenticated_actor.agent.display_name
                    if authenticated_actor.agent is not None
                    else None
                ),
                authenticated_api_key_hash=(
                    hash_api_key(authenticated_actor.api_key)
                    if authenticated_actor.api_key is not None
                    else None
                ),
                authenticated_human_user_id=authenticated_actor.human_user_id,
                request=create_request,
            )
        except MatchLobbyCreationError as exc:
            raise ApiError(
                status_code=(
                    HTTPStatus.UNAUTHORIZED
                    if exc.code in {"invalid_api_key", "invalid_player_auth"}
                    else HTTPStatus.BAD_REQUEST
                ),
                code=exc.code,
                message=exc.message,
            ) from exc

        registry.seed_match(created_lobby.record)
        return created_lobby.response

    @router.post(
        "/matches/{match_id}/start",
        response_model=MatchLobbyStartResponse,
        responses=_authenticated_lobby_route_responses(
            HTTPStatus.NOT_FOUND,
            HTTPStatus.FORBIDDEN,
            HTTPStatus.CONFLICT,
            HTTPStatus.SERVICE_UNAVAILABLE,
        ),
    )
    async def start_match_lobby_route(
        match_id: str,
        registry: InMemoryMatchRegistry = registry_dependency,
        api_key: ApiKeyHeader = None,
        authorization: AuthorizationHeader = None,
    ) -> MatchLobbyStartResponse:
        if history_database_url is None and api_key is None and authorization is None:
            raise ApiError(
                status_code=HTTPStatus.UNAUTHORIZED,
                code="invalid_api_key",
                message="A valid active X-API-Key header is required.",
            )
        authenticated_actor = app_services.resolve_authenticated_lobby_actor(
            registry=registry,
            api_key=api_key,
            authorization=authorization,
        )
        if history_database_url is None:
            raise ApiError(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                code="match_lobby_start_unavailable",
                message="Authenticated lobby start is only available in DB-backed mode.",
            )
        try:
            started_lobby = start_match_lobby(
                database_url=history_database_url,
                match_id=match_id,
                authenticated_api_key_hash=(
                    hash_api_key(authenticated_actor.api_key)
                    if authenticated_actor.api_key is not None
                    else None
                ),
                authenticated_human_user_id=authenticated_actor.human_user_id,
            )
        except MatchLobbyStartError as exc:
            status_code = HTTPStatus.BAD_REQUEST
            if exc.code in {"invalid_api_key", "invalid_player_auth"}:
                status_code = HTTPStatus.UNAUTHORIZED
            elif exc.code == "match_not_found":
                status_code = HTTPStatus.NOT_FOUND
            elif exc.code == "match_start_forbidden":
                status_code = HTTPStatus.FORBIDDEN
            elif exc.code in {
                "match_lobby_not_ready",
                "match_already_active",
                "match_already_completed",
                "match_not_startable",
            }:
                status_code = HTTPStatus.CONFLICT
            raise ApiError(
                status_code=status_code,
                code=exc.code,
                message=exc.message,
            ) from exc

        registry.seed_match(started_lobby.record)
        await ensure_match_running(match_id)
        return started_lobby.response

    return router
