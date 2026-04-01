"""FastAPI app-wiring helpers for the Iron Council server."""

from .authenticated_match_routes import build_authenticated_match_router
from .errors import API_ERROR_RESPONSE_SCHEMA, ApiError, register_error_handlers
from .public_routes import build_public_api_router, register_public_metadata_routes
from .realtime_routes import register_realtime_routes

__all__ = [
    "API_ERROR_RESPONSE_SCHEMA",
    "ApiError",
    "build_authenticated_match_router",
    "build_public_api_router",
    "register_error_handlers",
    "register_public_metadata_routes",
    "register_realtime_routes",
]
