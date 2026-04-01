from collections.abc import Callable
from http import HTTPStatus

from fastapi import APIRouter, Depends

from server.agent_registry import (
    InMemoryMatchRegistry,
    MatchRecord,
)
from server.models.api import AuthenticatedAgentContext

from .app_services import ApiKeyHeader, AppServices
from .authenticated_match_alliance_routes import build_authenticated_match_alliance_router
from .authenticated_match_command_routes import build_authenticated_match_command_router
from .authenticated_match_messaging_routes import build_authenticated_match_messaging_router
from .authenticated_match_route_helpers import BroadcastCurrentMatch
from .authenticated_match_treaty_routes import build_authenticated_match_treaty_router
from .errors import ApiError

RegistryProvider = Callable[..., InMemoryMatchRegistry]


def build_authenticated_match_router(
    *,
    match_registry_provider: RegistryProvider,
    app_services: AppServices,
    broadcast_current_match: BroadcastCurrentMatch,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    registry_dependency = Depends(match_registry_provider)

    def require_match_record(*, registry: InMemoryMatchRegistry, match_id: str) -> MatchRecord:
        record = registry.get_match(match_id)
        if record is None:
            raise ApiError(
                status_code=HTTPStatus.NOT_FOUND,
                code="match_not_found",
                message=f"Match '{match_id}' was not found.",
            )
        return record

    def resolve_authenticated_agent(
        registry: InMemoryMatchRegistry = registry_dependency,
        api_key: ApiKeyHeader = None,
    ) -> AuthenticatedAgentContext:
        return app_services.get_authenticated_agent(
            registry=registry,
            api_key=api_key,
        )

    authenticated_agent_dependency = Depends(resolve_authenticated_agent)
    router.include_router(
        build_authenticated_match_command_router(
            registry_dependency=registry_dependency,
            authenticated_agent_dependency=authenticated_agent_dependency,
            require_match_record=require_match_record,
            app_services=app_services,
            broadcast_current_match=broadcast_current_match,
        )
    )
    router.include_router(
        build_authenticated_match_messaging_router(
            registry_dependency=registry_dependency,
            authenticated_agent_dependency=authenticated_agent_dependency,
            require_match_record=require_match_record,
            app_services=app_services,
            broadcast_current_match=broadcast_current_match,
        )
    )
    router.include_router(
        build_authenticated_match_treaty_router(
            registry_dependency=registry_dependency,
            authenticated_agent_dependency=authenticated_agent_dependency,
            require_match_record=require_match_record,
            app_services=app_services,
            broadcast_current_match=broadcast_current_match,
        )
    )
    router.include_router(
        build_authenticated_match_alliance_router(
            registry_dependency=registry_dependency,
            authenticated_agent_dependency=authenticated_agent_dependency,
            require_match_record=require_match_record,
            app_services=app_services,
            broadcast_current_match=broadcast_current_match,
        )
    )

    return router
