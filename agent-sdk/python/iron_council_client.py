from __future__ import annotations

import asyncio
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any, TypeVar, cast

import httpx
from pydantic import BaseModel
from server.models.api import (
    AgentProfileResponse,
    AllianceAction,
    AllianceActionAcceptanceResponse,
    AllianceActionRequest,
    AllianceListResponse,
    ApiErrorResponse,
    MatchJoinRequest,
    MatchJoinResponse,
    MatchListResponse,
    MatchMessageCreateRequest,
    MatchMessageInboxResponse,
    MessageAcceptanceResponse,
    MessageChannel,
    OrderAcceptanceResponse,
    TreatyAction,
    TreatyActionAcceptanceResponse,
    TreatyActionRequest,
    TreatyListResponse,
    TreatyType,
)
from server.models.fog import AgentStateProjection
from server.models.orders import OrderBatch

ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)


class IronCouncilApiError(Exception):
    def __init__(
        self,
        *,
        status_code: int | None,
        error_code: str,
        message: str,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.message = message

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return (
            "IronCouncilApiError("
            f"status_code={self.status_code!r}, "
            f"error_code={self.error_code!r}, "
            f"message={self.message!r})"
        )


class IronCouncilClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        transport: httpx.BaseTransport | httpx.AsyncBaseTransport | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._transport = transport
        self._timeout = timeout

    def __repr__(self) -> str:
        return (
            "IronCouncilClient("
            f"base_url={self._base_url!r}, "
            "api_key='***redacted***', "
            f"timeout={self._timeout!r})"
        )

    def list_matches(self) -> MatchListResponse:
        return self._request_json("GET", "/api/v1/matches", response_model=MatchListResponse)

    def get_current_agent_profile(self) -> AgentProfileResponse:
        return self._request_json(
            "GET",
            "/api/v1/agent/profile",
            response_model=AgentProfileResponse,
        )

    def join_match(self, match_id: str) -> MatchJoinResponse:
        return self._request_json(
            "POST",
            f"/api/v1/matches/{match_id}/join",
            json_body=MatchJoinRequest(match_id=match_id),
            response_model=MatchJoinResponse,
        )

    def get_match_state(self, match_id: str) -> AgentStateProjection:
        return self._request_json(
            "GET",
            f"/api/v1/matches/{match_id}/state",
            response_model=AgentStateProjection,
        )

    def submit_orders(
        self,
        match_id: str,
        *,
        tick: int,
        orders: OrderBatch | Mapping[str, Any],
    ) -> OrderAcceptanceResponse:
        return self._request_json(
            "POST",
            f"/api/v1/matches/{match_id}/orders",
            json_body={
                "match_id": match_id,
                "tick": tick,
                "orders": self._model_dump(orders),
            },
            response_model=OrderAcceptanceResponse,
        )

    def get_messages(self, match_id: str) -> MatchMessageInboxResponse:
        return self._request_json(
            "GET",
            f"/api/v1/matches/{match_id}/messages",
            response_model=MatchMessageInboxResponse,
        )

    def send_message(
        self,
        match_id: str,
        *,
        tick: int,
        channel: MessageChannel,
        content: str,
        recipient_id: str | None = None,
    ) -> MessageAcceptanceResponse:
        return self._request_json(
            "POST",
            f"/api/v1/matches/{match_id}/messages",
            json_body=MatchMessageCreateRequest(
                match_id=match_id,
                tick=tick,
                channel=channel,
                recipient_id=recipient_id,
                content=content,
            ),
            response_model=MessageAcceptanceResponse,
        )

    def get_treaties(self, match_id: str) -> TreatyListResponse:
        return self._request_json(
            "GET",
            f"/api/v1/matches/{match_id}/treaties",
            response_model=TreatyListResponse,
        )

    def act_on_treaty(
        self,
        match_id: str,
        *,
        counterparty_id: str,
        action: TreatyAction,
        treaty_type: TreatyType,
    ) -> TreatyActionAcceptanceResponse:
        return self._request_json(
            "POST",
            f"/api/v1/matches/{match_id}/treaties",
            json_body=TreatyActionRequest(
                match_id=match_id,
                counterparty_id=counterparty_id,
                action=action,
                treaty_type=treaty_type,
            ),
            response_model=TreatyActionAcceptanceResponse,
        )

    def get_alliances(self, match_id: str) -> AllianceListResponse:
        return self._request_json(
            "GET",
            f"/api/v1/matches/{match_id}/alliances",
            response_model=AllianceListResponse,
        )

    def act_on_alliance(
        self,
        match_id: str,
        *,
        action: AllianceAction,
        alliance_id: str | None = None,
        name: str | None = None,
    ) -> AllianceActionAcceptanceResponse:
        return self._request_json(
            "POST",
            f"/api/v1/matches/{match_id}/alliances",
            json_body=AllianceActionRequest(
                match_id=match_id,
                action=action,
                alliance_id=alliance_id,
                name=name,
            ),
            response_model=AllianceActionAcceptanceResponse,
        )

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        response_model: type[ResponseModelT],
        json_body: BaseModel | Mapping[str, Any] | None = None,
    ) -> ResponseModelT:
        try:
            response = self._send_request(
                method,
                path,
                json_body=None if json_body is None else self._model_dump(json_body),
            )
        except httpx.HTTPError as exc:
            raise IronCouncilApiError(
                status_code=None,
                error_code="transport_error",
                message="Request to Iron Council API failed.",
            ) from exc

        if response.status_code >= HTTPStatus.BAD_REQUEST:
            self._raise_api_error(response)

        return response_model.model_validate(response.json())

    def _raise_api_error(self, response: httpx.Response) -> None:
        error_code = "http_error"
        message = f"Iron Council API request failed with status {response.status_code}."
        try:
            error_payload = ApiErrorResponse.model_validate(response.json())
        except Exception:
            pass
        else:
            error_code = error_payload.error.code
            message = error_payload.error.message

        raise IronCouncilApiError(
            status_code=response.status_code,
            error_code=error_code,
            message=message,
        )

    def _send_request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None,
    ) -> httpx.Response:
        if self._transport is not None and hasattr(self._transport, "handle_async_request"):
            return asyncio.run(self._send_async_request(method, path, json_body=json_body))

        with httpx.Client(
            base_url=self._base_url,
            headers={"X-API-Key": self._api_key},
            timeout=self._timeout,
            transport=self._transport,
        ) as client:
            return client.request(method, path, json=json_body)

    async def _send_async_request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None,
    ) -> httpx.Response:
        async with httpx.AsyncClient(
            base_url=self._base_url,
            headers={"X-API-Key": self._api_key},
            timeout=self._timeout,
            transport=cast(httpx.AsyncBaseTransport | None, self._transport),
        ) as client:
            return await client.request(method, path, json=json_body)

    @staticmethod
    def _model_dump(value: BaseModel | Mapping[str, Any]) -> dict[str, Any]:
        if isinstance(value, BaseModel):
            return dict(value.model_dump(mode="json"))
        return dict(value)
