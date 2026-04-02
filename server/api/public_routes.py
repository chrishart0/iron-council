from __future__ import annotations

from fastapi import APIRouter, FastAPI

from .public_history_routes import build_public_history_router
from .public_match_routes import (
    PublicRosterBuilder,
    PublicStatusPriority,
    RegistryProvider,
    build_public_match_router,
)
from .public_summary_routes import build_public_summary_router


def register_public_metadata_routes(app: FastAPI) -> None:
    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "service": app.title,
            "status": "ok",
            "version": app.version,
        }

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}


def build_public_api_router(
    *,
    match_registry_provider: RegistryProvider,
    history_database_url: str | None,
    public_match_status_priority: PublicStatusPriority,
    build_in_memory_public_match_roster: PublicRosterBuilder,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    router.include_router(build_public_summary_router(history_database_url=history_database_url))

    # Keep static `/matches/completed` above the dynamic `/matches/{match_id}` route.
    router.include_router(
        build_public_match_router(
            match_registry_provider=match_registry_provider,
            history_database_url=history_database_url,
            public_match_status_priority=public_match_status_priority,
            build_in_memory_public_match_roster=build_in_memory_public_match_roster,
        )
    )
    router.include_router(build_public_history_router(history_database_url=history_database_url))

    return router
