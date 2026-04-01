from __future__ import annotations

from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from server.models.api import ApiErrorDetail, ApiErrorResponse


class ApiError(Exception):
    def __init__(self, *, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


API_ERROR_RESPONSE_SCHEMA: dict[str, Any] = {"model": ApiErrorResponse}


def _build_validation_error_response(*, code: str, message: str) -> JSONResponse:
    payload = ApiErrorResponse(error=ApiErrorDetail(code=code, message=message))
    return JSONResponse(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        content=payload.model_dump(mode="json"),
    )


def _message_validation_error_response(exc: RequestValidationError) -> JSONResponse:
    for error in exc.errors():
        location = list(error.get("loc", ()))
        error_type = error.get("type")
        if location == ["body", "content"] and error_type == "string_too_short":
            return _build_validation_error_response(
                code="invalid_message_content",
                message="Message content must be at least 1 character long.",
            )
        if location and location[0] == "body" and error_type == "missing":
            return _build_validation_error_response(
                code="invalid_message_request",
                message="Message request is missing required fields.",
            )

    return _build_validation_error_response(
        code="invalid_message_request",
        message="Message request validation failed.",
    )


def _group_chat_validation_error_response(exc: RequestValidationError) -> JSONResponse:
    for error in exc.errors():
        location = list(error.get("loc", ()))
        error_type = error.get("type")
        if location == ["body", "name"] and error_type == "string_too_short":
            return _build_validation_error_response(
                code="invalid_group_chat_name",
                message="Group chat name must be at least 1 character long.",
            )
        if location == ["body", "member_ids"] and error_type == "too_short":
            return _build_validation_error_response(
                code="invalid_group_chat_members",
                message="Group chat creation requires at least 1 invited member.",
            )
        if location == ["body", "content"] and error_type == "string_too_short":
            return _build_validation_error_response(
                code="invalid_message_content",
                message="Message content must be at least 1 character long.",
            )
        if location and location[0] == "body" and error_type == "missing":
            return _build_validation_error_response(
                code="invalid_group_chat_request",
                message="Group chat request is missing required fields.",
            )

    return _build_validation_error_response(
        code="invalid_group_chat_request",
        message="Group chat request validation failed.",
    )


def _treaty_validation_error_response(exc: RequestValidationError) -> JSONResponse:
    for error in exc.errors():
        location = list(error.get("loc", ()))
        error_type = error.get("type")
        if location and location[0] == "body" and error_type == "missing":
            return _build_validation_error_response(
                code="invalid_treaty_request",
                message="Treaty request is missing required fields.",
            )
        if location == ["body", "action"] and error_type == "literal_error":
            return _build_validation_error_response(
                code="invalid_treaty_action",
                message="Treaty action must be one of: propose, accept, withdraw.",
            )
        if location == ["body", "treaty_type"] and error_type == "literal_error":
            return _build_validation_error_response(
                code="invalid_treaty_type",
                message="Treaty type must be one of: non_aggression, defensive, trade.",
            )

    return _build_validation_error_response(
        code="invalid_treaty_request",
        message="Treaty request validation failed.",
    )


def _alliance_validation_error_response(exc: RequestValidationError) -> JSONResponse:
    for error in exc.errors():
        location = list(error.get("loc", ()))
        error_type = error.get("type")
        error_message = str(error.get("msg", "")).lower()
        if location and location[0] == "body" and error_type == "missing":
            return _build_validation_error_response(
                code="invalid_alliance_request",
                message="Alliance request is missing required fields.",
            )
        if location == ["body", "action"] and error_type == "literal_error":
            return _build_validation_error_response(
                code="invalid_alliance_action",
                message="Alliance action must be one of: create, join, leave.",
            )
        if "alliance create does not accept alliance_id" in error_message:
            return _build_validation_error_response(
                code="invalid_alliance_request",
                message="Alliance create does not accept alliance_id.",
            )
        if "alliance create requires name" in error_message:
            return _build_validation_error_response(
                code="invalid_alliance_request",
                message="Alliance create requires name.",
            )
        if "alliance join requires alliance_id" in error_message:
            return _build_validation_error_response(
                code="invalid_alliance_request",
                message="Alliance join requires alliance_id.",
            )
        if "alliance join does not accept name" in error_message:
            return _build_validation_error_response(
                code="invalid_alliance_request",
                message="Alliance join does not accept name.",
            )
        if "alliance leave does not accept alliance_id" in error_message:
            return _build_validation_error_response(
                code="invalid_alliance_request",
                message="Alliance leave does not accept alliance_id.",
            )
        if "alliance leave does not accept name" in error_message:
            return _build_validation_error_response(
                code="invalid_alliance_request",
                message="Alliance leave does not accept name.",
            )

    return _build_validation_error_response(
        code="invalid_alliance_request",
        message="Alliance request validation failed.",
    )


def _join_validation_error_response(exc: RequestValidationError) -> JSONResponse:
    for error in exc.errors():
        location = list(error.get("loc", ()))
        error_type = error.get("type")
        if location and location[0] == "body" and error_type == "missing":
            return _build_validation_error_response(
                code="invalid_join_request",
                message="Join request is missing required fields.",
            )

    return _build_validation_error_response(
        code="invalid_join_request",
        message="Join request validation failed.",
    )


def _create_match_validation_error_response(exc: RequestValidationError) -> JSONResponse:
    for error in exc.errors():
        location = list(error.get("loc", ()))
        error_type = error.get("type")
        if location and location[0] == "body" and error_type == "missing":
            return _build_validation_error_response(
                code="invalid_match_lobby_request",
                message="Match lobby request is missing required fields.",
            )
        if location == ["body", "map"] and error_type == "literal_error":
            return _build_validation_error_response(
                code="invalid_match_map",
                message="Match map must be 'britain'.",
            )

    return _build_validation_error_response(
        code="invalid_match_lobby_request",
        message="Match lobby request validation failed.",
    )


def _command_validation_error_response(exc: RequestValidationError) -> JSONResponse:
    for error in exc.errors():
        location = list(error.get("loc", ()))
        error_type = error.get("type")
        error_message = str(error.get("msg", "")).lower()
        if (
            len(location) == 4
            and location[0] == "body"
            and location[1] == "messages"
            and isinstance(location[2], int)
            and location[3] == "content"
            and error_type == "string_too_short"
        ):
            return _build_validation_error_response(
                code="invalid_message_content",
                message="Message content must be at least 1 character long.",
            )
        if (
            len(location) == 4
            and location[0] == "body"
            and location[1] == "treaties"
            and isinstance(location[2], int)
            and location[3] == "action"
            and error_type == "literal_error"
        ):
            return _build_validation_error_response(
                code="invalid_treaty_action",
                message="Treaty action must be one of: propose, accept, withdraw.",
            )
        if (
            len(location) == 4
            and location[0] == "body"
            and location[1] == "treaties"
            and isinstance(location[2], int)
            and location[3] == "treaty_type"
            and error_type == "literal_error"
        ):
            return _build_validation_error_response(
                code="invalid_treaty_type",
                message="Treaty type must be one of: non_aggression, defensive, trade.",
            )
        if location and location[0] == "body" and error_type == "missing":
            return _build_validation_error_response(
                code="invalid_command_request",
                message="Command request is missing required fields.",
            )
        if "alliance create does not accept alliance_id" in error_message:
            return _build_validation_error_response(
                code="invalid_alliance_request",
                message="Alliance create does not accept alliance_id.",
            )
        if "alliance create requires name" in error_message:
            return _build_validation_error_response(
                code="invalid_alliance_request",
                message="Alliance create requires name.",
            )
        if "alliance join requires alliance_id" in error_message:
            return _build_validation_error_response(
                code="invalid_alliance_request",
                message="Alliance join requires alliance_id.",
            )
        if "alliance join does not accept name" in error_message:
            return _build_validation_error_response(
                code="invalid_alliance_request",
                message="Alliance join does not accept name.",
            )
        if "alliance leave does not accept alliance_id" in error_message:
            return _build_validation_error_response(
                code="invalid_alliance_request",
                message="Alliance leave does not accept alliance_id.",
            )
        if "alliance leave does not accept name" in error_message:
            return _build_validation_error_response(
                code="invalid_alliance_request",
                message="Alliance leave does not accept name.",
            )

    return _build_validation_error_response(
        code="invalid_command_request",
        message="Command request validation failed.",
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        payload = ApiErrorResponse(error=ApiErrorDetail(code=exc.code, message=exc.message))
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump(mode="json"))

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        if request.method == "POST" and request.url.path == "/api/v1/matches":
            return _create_match_validation_error_response(exc)
        if request.url.path.startswith("/api/v1/matches/") and request.url.path.endswith(
            ("/command", "/commands")
        ):
            return _command_validation_error_response(exc)
        if request.url.path.startswith("/api/v1/matches/") and "/group-chats" in request.url.path:
            return _group_chat_validation_error_response(exc)
        if request.url.path.startswith("/api/v1/matches/") and request.url.path.endswith(
            "/messages"
        ):
            return _message_validation_error_response(exc)
        if request.url.path.startswith("/api/v1/matches/") and request.url.path.endswith(
            "/treaties"
        ):
            return _treaty_validation_error_response(exc)
        if request.url.path.startswith("/api/v1/matches/") and request.url.path.endswith(
            "/alliances"
        ):
            return _alliance_validation_error_response(exc)
        if request.url.path.startswith("/api/v1/matches/") and request.url.path.endswith("/join"):
            return _join_validation_error_response(exc)
        return await request_validation_exception_handler(request, exc)
