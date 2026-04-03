from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
from typing import Annotated, Literal

from fastapi import Header
from sqlalchemy.orm import Session, sessionmaker

from server.agent_registry import InMemoryMatchRegistry, MatchAccessError
from server.auth import (
    HumanJwtValidationError,
    extract_bearer_token,
    validate_human_jwt,
)
from server.db.identity import (
    resolve_authenticated_agent_context,
    resolve_authenticated_agent_context_from_db,
    resolve_human_player_id,
    resolve_human_player_id_from_db,
    resolve_owned_agent_context,
    resolve_owned_agent_context_from_db,
)
from server.models.api import AuthenticatedAgentContext
from server.settings import Settings

from .errors import ApiError

ApiKeyHeader = Annotated[str | None, Header(alias="X-API-Key")]
AuthorizationHeader = Annotated[str | None, Header(alias="Authorization")]


@dataclass(frozen=True, slots=True)
class AuthenticatedLobbyActor:
    kind: Literal["agent", "human"]
    agent: AuthenticatedAgentContext | None = None
    api_key: str | None = None
    human_user_id: str | None = None


@dataclass(frozen=True, slots=True)
class AppServices:
    settings: Settings
    history_database_url: str | None
    history_db_session_factory: sessionmaker[Session] | None = None

    def get_authenticated_agent(
        self,
        *,
        registry: InMemoryMatchRegistry,
        api_key: str | None,
    ) -> AuthenticatedAgentContext:
        authenticated_agent = self.resolve_authenticated_agent_context(
            registry=registry,
            api_key=api_key,
        )
        if authenticated_agent is None:
            raise ApiError(
                status_code=HTTPStatus.UNAUTHORIZED,
                code="invalid_api_key",
                message="A valid active X-API-Key header is required.",
            )
        return authenticated_agent

    def resolve_authenticated_agent_context(
        self,
        *,
        registry: InMemoryMatchRegistry,
        api_key: str | None,
    ) -> AuthenticatedAgentContext | None:
        if api_key is None:
            return None

        authenticated_agent = registry.resolve_authenticated_agent(api_key)
        if authenticated_agent is None:
            if self.history_db_session_factory is not None:
                with self.history_db_session_factory() as session:
                    authenticated_agent = resolve_authenticated_agent_context(
                        session=session,
                        api_key=api_key,
                    )
            elif self.history_database_url is not None:
                authenticated_agent = resolve_authenticated_agent_context_from_db(
                    database_url=self.history_database_url,
                    api_key=api_key,
                )
        return authenticated_agent

    def resolve_authenticated_human_user_id(
        self,
        *,
        authorization: str | None,
    ) -> str:
        if authorization is None:
            raise ApiError(
                status_code=HTTPStatus.UNAUTHORIZED,
                code="invalid_player_auth",
                message="Player routes require a valid Bearer token or active X-API-Key header.",
            )

        try:
            token = extract_bearer_token(authorization)
            human_context = validate_human_jwt(token, settings=self.settings)
        except HumanJwtValidationError as exc:
            raise ApiError(
                status_code=HTTPStatus.UNAUTHORIZED,
                code=exc.code,
                message=exc.message,
            ) from exc
        return human_context.user_id

    def require_authenticated_human_user_id(
        self,
        *,
        authorization: str | None,
    ) -> str:
        if authorization is None:
            raise ApiError(
                status_code=HTTPStatus.UNAUTHORIZED,
                code="invalid_human_token",
                message="A valid human Bearer token is required.",
            )

        try:
            token = extract_bearer_token(authorization)
            human_context = validate_human_jwt(token, settings=self.settings)
        except HumanJwtValidationError as exc:
            raise ApiError(
                status_code=HTTPStatus.UNAUTHORIZED,
                code=exc.code,
                message=exc.message,
            ) from exc
        return human_context.user_id

    def require_owned_agent_context(
        self,
        *,
        authorization: str | None,
        agent_id: str,
    ) -> tuple[str, AuthenticatedAgentContext]:
        if self.history_database_url is None:
            raise ApiError(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                code="guided_session_unavailable",
                message="Owned agent guided-session reads are only available in DB-backed mode.",
            )

        user_id = self.require_authenticated_human_user_id(authorization=authorization)
        if self.history_db_session_factory is not None:
            with self.history_db_session_factory() as session:
                owned_agent = resolve_owned_agent_context(
                    session=session,
                    user_id=user_id,
                    agent_id=agent_id,
                )
        else:
            owned_agent = resolve_owned_agent_context_from_db(
                database_url=self.history_database_url,
                user_id=user_id,
                agent_id=agent_id,
            )
        if owned_agent is None:
            raise ApiError(
                status_code=HTTPStatus.FORBIDDEN,
                code="agent_not_owned",
                message=f"Authenticated human user '{user_id}' does not own agent '{agent_id}'.",
            )
        return user_id, owned_agent

    def resolve_authenticated_lobby_actor(
        self,
        *,
        registry: InMemoryMatchRegistry,
        api_key: str | None,
        authorization: str | None,
    ) -> AuthenticatedLobbyActor:
        authenticated_agent = self.resolve_authenticated_agent_context(
            registry=registry,
            api_key=api_key,
        )
        if authenticated_agent is not None and api_key is not None:
            return AuthenticatedLobbyActor(
                kind="agent",
                agent=authenticated_agent,
                api_key=api_key,
            )
        if api_key is not None:
            raise ApiError(
                status_code=HTTPStatus.UNAUTHORIZED,
                code="invalid_api_key",
                message="A valid active X-API-Key header is required.",
            )
        if authorization is None and self.settings.human_jwt_secret is None:
            raise ApiError(
                status_code=HTTPStatus.UNAUTHORIZED,
                code="invalid_api_key",
                message="A valid active X-API-Key header is required.",
            )
        return AuthenticatedLobbyActor(
            kind="human",
            human_user_id=self.resolve_authenticated_human_user_id(
                authorization=authorization,
            ),
        )

    def require_joined_player_id(
        self,
        *,
        registry: InMemoryMatchRegistry,
        match_id: str,
        authenticated_agent: AuthenticatedAgentContext,
    ) -> str:
        try:
            return registry.require_joined_player_id(
                match_id=match_id,
                agent_id=authenticated_agent.agent_id,
            )
        except MatchAccessError as exc:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code=exc.code,
                message=exc.message,
            ) from exc

    def require_joined_human_player_id(
        self,
        *,
        registry: InMemoryMatchRegistry,
        match_id: str,
        user_id: str,
    ) -> str:
        try:
            return registry.require_joined_human_player_id(match_id=match_id, user_id=user_id)
        except MatchAccessError as exc:
            raise ApiError(
                status_code=HTTPStatus.BAD_REQUEST,
                code=exc.code,
                message=exc.message,
            ) from exc

    def resolve_human_player_id(
        self,
        *,
        registry: InMemoryMatchRegistry,
        match_id: str,
        user_id: str,
    ) -> str:
        if registry.get_match(match_id) is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )
        if self.history_database_url is not None:
            if self.history_db_session_factory is not None:
                with self.history_db_session_factory() as session:
                    db_player_id = resolve_human_player_id(
                        session=session,
                        match_id=match_id,
                        user_id=user_id,
                    )
            else:
                db_player_id = resolve_human_player_id_from_db(
                    database_url=self.history_database_url,
                    match_id=match_id,
                    user_id=user_id,
                )
            if db_player_id is not None:
                return db_player_id
        return self.require_joined_human_player_id(
            registry=registry,
            match_id=match_id,
            user_id=user_id,
        )

    def resolve_match_player_id(
        self,
        *,
        registry: InMemoryMatchRegistry,
        match_id: str,
        api_key: str | None,
        authorization: str | None,
    ) -> str:
        if api_key is not None:
            authenticated_agent = self.resolve_authenticated_agent_context(
                registry=registry,
                api_key=api_key,
            )
            if authenticated_agent is None:
                raise ApiError(
                    status_code=HTTPStatus.UNAUTHORIZED,
                    code="invalid_api_key",
                    message="A valid active X-API-Key header is required.",
                )
            return self.require_joined_player_id(
                registry=registry,
                match_id=match_id,
                authenticated_agent=authenticated_agent,
            )
        if authorization is None:
            raise ApiError(
                status_code=HTTPStatus.UNAUTHORIZED,
                code="invalid_player_auth",
                message="Player routes require a valid Bearer token or active X-API-Key header.",
            )
        return self.resolve_human_player_id(
            registry=registry,
            match_id=match_id,
            user_id=self.resolve_authenticated_human_user_id(
                authorization=authorization,
            ),
        )

    def resolve_websocket_player_viewer(
        self,
        *,
        registry: InMemoryMatchRegistry,
        match_id: str,
        player_id: str | None,
        token: str | None,
    ) -> str:
        if token is None:
            raise ApiError(
                status_code=HTTPStatus.UNAUTHORIZED,
                code="invalid_websocket_auth",
                message=(
                    "Player websocket connections require a valid human JWT token query parameter."
                ),
            )
        try:
            human_context = validate_human_jwt(token, settings=self.settings)
        except HumanJwtValidationError as exc:
            raise ApiError(
                status_code=HTTPStatus.UNAUTHORIZED,
                code="invalid_websocket_auth",
                message=exc.message,
            ) from exc

        resolved_player_id = self.resolve_human_player_id(
            registry=registry,
            match_id=match_id,
            user_id=human_context.user_id,
        )
        if player_id is not None and resolved_player_id != player_id:
            raise ApiError(
                status_code=HTTPStatus.FORBIDDEN,
                code="player_auth_mismatch",
                message=(
                    f"Player websocket auth resolved to player '{resolved_player_id}', not "
                    f"'{player_id}'."
                ),
            )
        return resolved_player_id
