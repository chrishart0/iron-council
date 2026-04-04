from collections.abc import Awaitable, Callable
from http import HTTPStatus
from typing import Any

from server.agent_registry import MatchRecord

from .abuse import authenticated_write_abuse_error_responses
from .errors import API_ERROR_RESPONSE_SCHEMA

MatchRecordResolver = Callable[..., MatchRecord]
BroadcastCurrentMatch = Callable[[str], Awaitable[None]]


def authenticated_route_responses(
    *status_codes: HTTPStatus,
) -> dict[int | str, dict[str, Any]]:
    return {
        int(HTTPStatus.UNAUTHORIZED): API_ERROR_RESPONSE_SCHEMA,
        **{int(status_code): API_ERROR_RESPONSE_SCHEMA for status_code in status_codes},
    }


def authenticated_write_route_responses(
    *status_codes: HTTPStatus,
) -> dict[int | str, dict[str, Any]]:
    return {
        **authenticated_route_responses(*status_codes),
        **authenticated_write_abuse_error_responses(),
    }
