from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import APIRouter

from server.agent_registry import InMemoryMatchRegistry

from .app_services import (
    AppServices,
)
from .authenticated_lobby_routes import build_authenticated_lobby_router
from .authenticated_read_routes import build_authenticated_read_router
from .authenticated_write_routes import build_authenticated_write_router


def build_authenticated_access_router(
    *,
    match_registry_provider: Callable[..., InMemoryMatchRegistry],
    app_services: AppServices,
    ensure_match_running: Callable[[str], Awaitable[None]],
) -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    router.include_router(
        build_authenticated_lobby_router(
            match_registry_provider=match_registry_provider,
            app_services=app_services,
            ensure_match_running=ensure_match_running,
        )
    )
    router.include_router(
        build_authenticated_read_router(
            match_registry_provider=match_registry_provider,
            app_services=app_services,
        )
    )
    router.include_router(
        build_authenticated_write_router(
            match_registry_provider=match_registry_provider,
            app_services=app_services,
        )
    )

    return router
