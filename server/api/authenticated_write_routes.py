from __future__ import annotations

from collections.abc import Callable
from http import HTTPStatus
from typing import Any

from fastapi import APIRouter, Depends

from server.agent_registry import InMemoryMatchRegistry, MatchJoinError
from server.auth import hash_api_key
from server.db.api_key_lifecycle import create_owned_api_key, revoke_owned_api_key
from server.db.registry import join_match as join_db_match
from server.models.api import (
    AuthenticatedOrderSubmissionRequest,
    MatchJoinRequest,
    MatchJoinResponse,
    OrderAcceptanceResponse,
    OwnedApiKeyCreateResponse,
    OwnedApiKeySummary,
)
from server.models.domain import MatchStatus
from server.models.orders import OrderEnvelope

from .app_services import ApiKeyHeader, AppServices, AuthorizationHeader
from .errors import API_ERROR_RESPONSE_SCHEMA, ApiError

RegistryProvider = Callable[..., InMemoryMatchRegistry]


def _authenticated_write_route_responses(
    *status_codes: HTTPStatus,
) -> dict[int | str, dict[str, Any]]:
    return {
        int(HTTPStatus.UNAUTHORIZED): API_ERROR_RESPONSE_SCHEMA,
        **{int(status_code): API_ERROR_RESPONSE_SCHEMA for status_code in status_codes},
    }


def build_authenticated_write_router(
    *,
    match_registry_provider: RegistryProvider,
    app_services: AppServices,
) -> APIRouter:
    router = APIRouter()
    registry_dependency = Depends(match_registry_provider)
    history_database_url = app_services.history_database_url

    @router.post(
        "/account/api-keys",
        response_model=OwnedApiKeyCreateResponse,
        status_code=HTTPStatus.CREATED,
        responses={
            int(HTTPStatus.UNAUTHORIZED): API_ERROR_RESPONSE_SCHEMA,
            int(HTTPStatus.SERVICE_UNAVAILABLE): API_ERROR_RESPONSE_SCHEMA,
        },
    )
    async def create_authenticated_human_api_key(
        authorization: AuthorizationHeader = None,
    ) -> OwnedApiKeyCreateResponse:
        if history_database_url is None:
            raise ApiError(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                code="api_key_lifecycle_unavailable",
                message="Owned API key lifecycle routes are only available in DB-backed mode.",
            )

        user_id = app_services.require_authenticated_human_user_id(authorization=authorization)
        raw_key, summary = create_owned_api_key(
            database_url=history_database_url,
            user_id=user_id,
        )
        return OwnedApiKeyCreateResponse(api_key=raw_key, summary=summary)

    @router.delete(
        "/account/api-keys/{key_id}",
        response_model=OwnedApiKeySummary,
        responses={
            int(HTTPStatus.UNAUTHORIZED): API_ERROR_RESPONSE_SCHEMA,
            int(HTTPStatus.NOT_FOUND): API_ERROR_RESPONSE_SCHEMA,
            int(HTTPStatus.SERVICE_UNAVAILABLE): API_ERROR_RESPONSE_SCHEMA,
        },
    )
    async def revoke_authenticated_human_api_key(
        key_id: str,
        authorization: AuthorizationHeader = None,
    ) -> OwnedApiKeySummary:
        if history_database_url is None:
            raise ApiError(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                code="api_key_lifecycle_unavailable",
                message="Owned API key lifecycle routes are only available in DB-backed mode.",
            )

        user_id = app_services.require_authenticated_human_user_id(authorization=authorization)
        summary = revoke_owned_api_key(
            database_url=history_database_url,
            user_id=user_id,
            key_id=key_id,
        )
        if summary is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="api_key_not_found",
                message=f"API key '{key_id}' was not found.",
            )
        return summary

    @router.post(
        "/matches/{match_id}/join",
        response_model=MatchJoinResponse,
        status_code=HTTPStatus.ACCEPTED,
        responses=_authenticated_write_route_responses(
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.NOT_FOUND,
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
    )
    async def join_match(
        match_id: str,
        join_request: MatchJoinRequest,
        registry: InMemoryMatchRegistry = registry_dependency,
        api_key: ApiKeyHeader = None,
        authorization: AuthorizationHeader = None,
    ) -> MatchJoinResponse:
        record = registry.get_match(match_id)
        if record is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )
        if api_key is None and authorization is None and record.status is not MatchStatus.LOBBY:
            raise ApiError(
                status_code=HTTPStatus.UNAUTHORIZED,
                code="invalid_api_key",
                message="A valid active X-API-Key header is required.",
            )
        if join_request.match_id != match_id:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code="match_id_mismatch",
                message=(
                    f"Join payload match_id '{join_request.match_id}' does not match route "
                    f"match '{match_id}'."
                ),
            )

        authenticated_actor = app_services.resolve_authenticated_lobby_actor(
            registry=registry,
            api_key=api_key,
            authorization=authorization,
        )
        try:
            if history_database_url is not None:
                joined_match = join_db_match(
                    database_url=history_database_url,
                    match_id=match_id,
                    authenticated_api_key_hash=(
                        hash_api_key(authenticated_actor.api_key)
                        if authenticated_actor.api_key is not None
                        else None
                    ),
                    authenticated_human_user_id=authenticated_actor.human_user_id,
                )
                registry.seed_match(joined_match.record)
                return joined_match.response
            if authenticated_actor.agent is None:
                raise ApiError(
                    status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                    code="match_join_unavailable",
                    message="Authenticated human joins are only available in DB-backed mode.",
                )
            return registry.join_match(
                match_id=match_id,
                agent_id=authenticated_actor.agent.agent_id,
            )
        except MatchJoinError as exc:
            status_code = HTTPStatus.BAD_REQUEST
            if exc.code in {"invalid_api_key", "invalid_player_auth"}:
                status_code = HTTPStatus.UNAUTHORIZED
            elif exc.code == "match_not_found":
                status_code = HTTPStatus.NOT_FOUND
            raise ApiError(status_code=status_code, code=exc.code, message=exc.message) from exc

    @router.post(
        "/matches/{match_id}/orders",
        response_model=OrderAcceptanceResponse,
        status_code=HTTPStatus.ACCEPTED,
        responses=_authenticated_write_route_responses(
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.NOT_FOUND,
        ),
    )
    async def submit_orders(
        match_id: str,
        submission: AuthenticatedOrderSubmissionRequest,
        registry: InMemoryMatchRegistry = registry_dependency,
        api_key: ApiKeyHeader = None,
        authorization: AuthorizationHeader = None,
    ) -> OrderAcceptanceResponse:
        record = registry.get_match(match_id)
        if record is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )
        if submission.match_id != match_id:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code="match_id_mismatch",
                message=(
                    f"Order payload match_id '{submission.match_id}' does not match route match "
                    f"'{match_id}'."
                ),
            )
        resolved_player_id = app_services.resolve_match_player_id(
            registry=registry,
            match_id=match_id,
            api_key=api_key,
            authorization=authorization,
        )
        if submission.tick != record.state.tick:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code="tick_mismatch",
                message=(
                    f"Order payload tick '{submission.tick}' does not match current match tick "
                    f"'{record.state.tick}'."
                ),
            )

        envelope = OrderEnvelope(
            match_id=submission.match_id,
            player_id=resolved_player_id,
            tick=submission.tick,
            orders=submission.orders,
        )
        submission_index = registry.record_submission(match_id=match_id, envelope=envelope)
        return OrderAcceptanceResponse(
            status="accepted",
            match_id=match_id,
            player_id=envelope.player_id,
            tick=envelope.tick,
            submission_index=submission_index,
        )

    return router
