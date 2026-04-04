from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, field
from http import HTTPStatus
from threading import Lock
from time import monotonic
from typing import Any

from fastapi import Depends, Request, WebSocket
from starlette.requests import HTTPConnection

from server.agent_registry import InMemoryMatchRegistry
from server.auth import hash_api_key
from server.settings import AuthenticatedWriteAbuseSettings

from .app_services import AppServices
from .errors import API_ERROR_RESPONSE_SCHEMA, ApiError

_HUMAN_ONLY_WRITE_ROUTE_PATHS = {
    "/api/v1/account/api-keys",
    "/api/v1/account/api-keys/{key_id}",
    "/api/v1/matches/{match_id}/agents/{agent_id}/guidance",
    "/api/v1/matches/{match_id}/agents/{agent_id}/override",
}
_PUBLIC_ENTRYPOINT_ROUTE_PATHS = {
    "/api/v1/matches",
    "/health/runtime",
}
_ROUTE_KEY_ALIASES = {
    "/ws/matches/{match_id}": "/ws/match/{match_id}",
}


def authenticated_write_abuse_error_responses() -> dict[int | str, dict[str, Any]]:
    return {
        int(HTTPStatus.REQUEST_ENTITY_TOO_LARGE): API_ERROR_RESPONSE_SCHEMA,
        int(HTTPStatus.TOO_MANY_REQUESTS): API_ERROR_RESPONSE_SCHEMA,
    }


def public_entrypoint_abuse_error_responses() -> dict[int | str, dict[str, Any]]:
    return {int(HTTPStatus.TOO_MANY_REQUESTS): API_ERROR_RESPONSE_SCHEMA}


@dataclass(slots=True)
class AuthenticatedWriteAbuseGuard:
    settings: AuthenticatedWriteAbuseSettings
    _request_windows: dict[tuple[str, str], deque[float]] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    async def enforce(
        self,
        *,
        request: Request,
        app_services: AppServices,
        registry: InMemoryMatchRegistry,
    ) -> None:
        max_body_bytes = self.settings.max_body_bytes
        if _content_length_exceeds_limit(request.headers, max_body_bytes=max_body_bytes):
            raise _payload_too_large_error(max_body_bytes=max_body_bytes)

        if len(await request.body()) > max_body_bytes:
            raise _payload_too_large_error(max_body_bytes=max_body_bytes)

        identity_key = self._resolve_identity_key(
            request=request,
            app_services=app_services,
            registry=registry,
        )
        if identity_key is None:
            return

        route_key = _resolve_route_key(request=request)
        if not self._consume_rate_allowance(identity_key=identity_key, route_key=route_key):
            raise _rate_limit_error(
                message=(
                    "Authenticated write burst limit exceeded for this caller on this route. "
                    f"Retry after the current {self.settings.rate_window_seconds}-second window."
                )
            )

    async def enforce_public_request(self, *, request: Request) -> None:
        route_key = _resolve_route_key(request=request)
        if route_key not in _PUBLIC_ENTRYPOINT_ROUTE_PATHS:
            return

        identity_key = _resolve_network_identity(connection=request)
        if not self._consume_rate_allowance(identity_key=identity_key, route_key=route_key):
            raise _rate_limit_error(
                message=(
                    "Public entrypoint burst limit exceeded for this caller on this route. "
                    f"Retry after the current {self.settings.rate_window_seconds}-second window."
                )
            )

    def enforce_websocket_handshake(self, *, websocket: WebSocket) -> None:
        route_key = _resolve_route_key(request=websocket)
        identity_key = _resolve_network_identity(connection=websocket)
        if not self._consume_rate_allowance(identity_key=identity_key, route_key=route_key):
            raise _rate_limit_error(
                message=(
                    "Websocket handshake burst limit exceeded for this caller on this route. "
                    f"Retry after the current {self.settings.rate_window_seconds}-second window."
                )
            )

    def _resolve_identity_key(
        self,
        *,
        request: Request,
        app_services: AppServices,
        registry: InMemoryMatchRegistry,
    ) -> str | None:
        route_path = _resolve_route_key(request=request)
        api_key = request.headers.get("X-API-Key")
        authorization = request.headers.get("Authorization")
        if route_path not in _HUMAN_ONLY_WRITE_ROUTE_PATHS and api_key is not None:
            authenticated_agent = app_services.resolve_authenticated_agent_context(
                registry=registry,
                api_key=api_key,
            )
            if authenticated_agent is None:
                return None
            return f"api-key:{hash_api_key(api_key)}"

        if authorization is None:
            return None

        try:
            human_user_id = app_services.resolve_authenticated_human_user_id(
                authorization=authorization
            )
        except ApiError:
            return None
        return f"human:{human_user_id}"

    def _consume_rate_allowance(self, *, identity_key: str, route_key: str) -> bool:
        now = monotonic()
        window_start = now - self.settings.rate_window_seconds
        request_key = (identity_key, route_key)
        with self._lock:
            request_times = self._request_windows.setdefault(request_key, deque())
            while request_times and request_times[0] <= window_start:
                request_times.popleft()
            if len(request_times) >= self.settings.rate_limit:
                return False
            request_times.append(now)
        return True


async def enforce_authenticated_write_abuse(request: Request) -> None:
    abuse_guard = getattr(request.app.state, "authenticated_write_abuse_guard", None)
    app_services = getattr(request.app.state, "app_services", None)
    registry = getattr(request.app.state, "match_registry", None)
    if abuse_guard is None or app_services is None or registry is None:
        return
    await abuse_guard.enforce(
        request=request,
        app_services=app_services,
        registry=registry,
    )


authenticated_write_abuse_dependency = Depends(enforce_authenticated_write_abuse)


async def enforce_public_entrypoint_abuse(request: Request) -> None:
    abuse_guard = getattr(request.app.state, "authenticated_write_abuse_guard", None)
    if abuse_guard is None:
        return
    await abuse_guard.enforce_public_request(request=request)


public_entrypoint_abuse_dependency = Depends(enforce_public_entrypoint_abuse)


def enforce_websocket_handshake_abuse(websocket: WebSocket) -> None:
    abuse_guard = getattr(websocket.app.state, "authenticated_write_abuse_guard", None)
    if abuse_guard is None:
        return
    abuse_guard.enforce_websocket_handshake(websocket=websocket)


def _content_length_exceeds_limit(
    headers: Mapping[str, str],
    *,
    max_body_bytes: int,
) -> bool:
    content_length = headers.get("content-length")
    if content_length is None:
        return False
    try:
        parsed_content_length = int(content_length)
    except ValueError:
        return False
    return parsed_content_length > max_body_bytes


def _payload_too_large_error(*, max_body_bytes: int) -> ApiError:
    return ApiError(
        status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
        code="payload_too_large",
        message=(
            "Authenticated write request body exceeds the configured limit of "
            f"{max_body_bytes} bytes."
        ),
    )


def _rate_limit_error(*, message: str) -> ApiError:
    return ApiError(
        status_code=HTTPStatus.TOO_MANY_REQUESTS,
        code="rate_limit_exceeded",
        message=message,
    )


def _resolve_route_key(*, request: HTTPConnection) -> str:
    route = request.scope.get("route")
    route_path = getattr(route, "path", None)
    if isinstance(route_path, str):
        return _ROUTE_KEY_ALIASES.get(route_path, route_path)
    return request.url.path


def _resolve_network_identity(*, connection: HTTPConnection) -> str:
    client = connection.client
    if client is not None:
        return f"network:{client.host}"

    return "network:unknown"
