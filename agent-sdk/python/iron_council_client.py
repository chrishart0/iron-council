from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from enum import IntEnum, StrEnum
from http import HTTPStatus
from typing import Annotated, Any, Literal, Protocol, Self, TypeVar

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_UPGRADE_TIER = 3
NonNegativeCount = Annotated[int, Field(ge=0)]
TickDuration = Annotated[int, Field(ge=0)]
PositiveCount = Annotated[int, Field(gt=0)]
PositiveTickDuration = Annotated[int, Field(gt=0)]
UpgradeLevel = Annotated[int, Field(ge=0, le=MAX_UPGRADE_TIER)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResourceType(StrEnum):
    FOOD = "food"
    PRODUCTION = "production"
    MONEY = "money"


class MatchStatus(StrEnum):
    LOBBY = "lobby"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class UpgradeTrack(StrEnum):
    ECONOMY = "economy"
    MILITARY = "military"
    FORTIFICATION = "fortification"


class FortificationTier(IntEnum):
    TRENCHES = 1
    BUNKERS = 2
    FORTRESS = 3


class ResourceState(StrictModel):
    food: NonNegativeCount
    production: NonNegativeCount
    money: NonNegativeCount


class CityUpgradeState(StrictModel):
    economy: UpgradeLevel
    military: UpgradeLevel
    fortification: UpgradeLevel


class BuildingQueueItem(StrictModel):
    type: UpgradeTrack
    tier: FortificationTier
    ticks_remaining: PositiveTickDuration


class VictoryState(StrictModel):
    leading_alliance: str | None = None
    cities_held: NonNegativeCount
    threshold: NonNegativeCount
    countdown_ticks_remaining: TickDuration | None = None


FogVisibility = Literal["full", "partial"]
UnknownField = Literal["unknown"]


class VisibleCityState(StrictModel):
    owner: str | None = None
    visibility: FogVisibility
    population: int | UnknownField
    resources: ResourceState | UnknownField
    upgrades: CityUpgradeState | UnknownField
    garrison: int | UnknownField
    building_queue: list[BuildingQueueItem] | UnknownField = Field(default_factory=list)


class VisibleArmyState(StrictModel):
    id: str
    owner: str
    visibility: FogVisibility
    troops: PositiveCount | UnknownField
    location: str | None = None
    destination: str | None = None
    path: list[str] | UnknownField | None = None
    ticks_remaining: TickDuration


class AgentStateProjection(StrictModel):
    match_id: str
    tick: int
    player_id: str
    resources: ResourceState
    cities: dict[str, VisibleCityState]
    visible_armies: list[VisibleArmyState] = Field(default_factory=list)
    alliance_id: str | None = None
    alliance_members: list[str] = Field(default_factory=list)
    victory: VictoryState


class MovementOrder(StrictModel):
    type: Literal["movement"] = Field(default="movement", exclude=True)
    army_id: str
    destination: str


class RecruitmentOrder(StrictModel):
    type: Literal["recruitment"] = Field(default="recruitment", exclude=True)
    city: str
    troops: PositiveCount


class UpgradeOrder(StrictModel):
    type: Literal["upgrade"] = Field(default="upgrade", exclude=True)
    city: str
    track: UpgradeTrack
    target_tier: FortificationTier


class TransferOrder(StrictModel):
    type: Literal["transfer"] = Field(default="transfer", exclude=True)
    sender: str | None = Field(default=None, exclude=True)
    to: str
    resource: ResourceType
    amount: PositiveCount


class OrderBatch(StrictModel):
    movements: list[MovementOrder] = Field(default_factory=list)
    recruitment: list[RecruitmentOrder] = Field(default_factory=list)
    upgrades: list[UpgradeOrder] = Field(default_factory=list)
    transfers: list[TransferOrder] = Field(default_factory=list)


class ApiErrorDetail(StrictModel):
    code: str
    message: str


class ApiErrorResponse(StrictModel):
    error: ApiErrorDetail


class MatchSummary(StrictModel):
    match_id: str
    status: MatchStatus
    map: str
    tick: TickDuration
    tick_interval_seconds: int = Field(gt=0)
    current_player_count: int = Field(ge=0)
    max_player_count: int = Field(ge=0)
    open_slot_count: int = Field(ge=0)


class MatchListResponse(StrictModel):
    matches: list[MatchSummary] = Field(default_factory=list)


class OrderAcceptanceResponse(StrictModel):
    status: Literal["accepted"]
    match_id: str
    player_id: str
    tick: TickDuration
    submission_index: int = Field(ge=0)


class MatchJoinRequest(StrictModel):
    match_id: str


class MatchLobbyCreateRequest(StrictModel):
    map: Literal["britain"]
    tick_interval_seconds: int = Field(gt=0)
    max_players: int = Field(gt=0)
    victory_city_threshold: int = Field(gt=0)
    starting_cities_per_player: int = Field(ge=0)


class MatchLobbyCreateResponse(MatchSummary):
    creator_player_id: str


class MatchLobbyStartResponse(MatchSummary):
    pass


class MatchJoinResponse(StrictModel):
    status: Literal["accepted"]
    match_id: str
    agent_id: str
    player_id: str


class AgentProfileRating(StrictModel):
    elo: int = Field(ge=0)
    provisional: bool


class AgentProfileHistory(StrictModel):
    matches_played: int = Field(ge=0)
    wins: int = Field(ge=0)
    losses: int = Field(ge=0)
    draws: int = Field(ge=0)


MessageChannel = Literal["world", "direct"]
CommandMessageChannel = Literal["world", "direct", "group"]
TreatyAction = Literal["propose", "accept", "withdraw"]
TreatyType = Literal["non_aggression", "defensive", "trade"]
TreatyStatus = Literal["proposed", "active", "honored", "broken_by_a", "broken_by_b", "withdrawn"]
AllianceAction = Literal["create", "join", "leave"]


class ProfileTreatyReputationSummary(StrictModel):
    signed: int = Field(ge=0)
    active: int = Field(ge=0)
    honored: int = Field(ge=0)
    withdrawn: int = Field(ge=0)
    broken_by_self: int = Field(ge=0)
    broken_by_counterparty: int = Field(ge=0)


class ProfileTreatyHistoryRecord(StrictModel):
    match_id: str
    counterparty_display_name: str
    treaty_type: TreatyType
    status: TreatyStatus
    signed_tick: TickDuration
    ended_tick: TickDuration | None = None
    broken_by_self: bool


class ProfileTreatyReputation(StrictModel):
    summary: ProfileTreatyReputationSummary
    history: list[ProfileTreatyHistoryRecord] = Field(default_factory=list)


class AgentProfileResponse(StrictModel):
    agent_id: str
    display_name: str
    is_seeded: bool
    rating: AgentProfileRating
    history: AgentProfileHistory
    treaty_reputation: ProfileTreatyReputation


class MatchMessageCreateRequest(StrictModel):
    match_id: str
    tick: TickDuration
    channel: MessageChannel
    recipient_id: str | None = None
    content: str = Field(min_length=1)


class MatchMessageRecord(StrictModel):
    message_id: int = Field(ge=0)
    channel: MessageChannel
    sender_id: str
    recipient_id: str | None = None
    tick: TickDuration
    content: str


class MatchMessageInboxResponse(StrictModel):
    match_id: str
    player_id: str
    messages: list[MatchMessageRecord] = Field(default_factory=list)


class MessageAcceptanceResponse(StrictModel):
    status: Literal["accepted"]
    match_id: str
    message_id: int = Field(ge=0)
    channel: MessageChannel
    sender_id: str
    recipient_id: str | None = None
    tick: TickDuration
    content: str


class GroupChatCreateRequest(StrictModel):
    match_id: str
    tick: TickDuration
    name: str = Field(min_length=1)
    member_ids: list[str] = Field(min_length=1)


class GroupChatRecord(StrictModel):
    group_chat_id: str
    name: str
    member_ids: list[str] = Field(default_factory=list)
    created_by: str
    created_tick: TickDuration


class GroupChatListResponse(StrictModel):
    match_id: str
    player_id: str
    group_chats: list[GroupChatRecord] = Field(default_factory=list)


class GroupChatCreateAcceptanceResponse(StrictModel):
    status: Literal["accepted"]
    match_id: str
    group_chat: GroupChatRecord


class GroupChatMessageCreateRequest(StrictModel):
    match_id: str
    tick: TickDuration
    content: str = Field(min_length=1)


class GroupChatMessageRecord(StrictModel):
    message_id: int = Field(ge=0)
    group_chat_id: str
    sender_id: str
    tick: TickDuration
    content: str


class GroupChatMessageListResponse(StrictModel):
    match_id: str
    group_chat_id: str
    player_id: str
    messages: list[GroupChatMessageRecord] = Field(default_factory=list)


class GroupChatMessageAcceptanceResponse(StrictModel):
    status: Literal["accepted"]
    match_id: str
    group_chat_id: str
    message: GroupChatMessageRecord


class TreatyActionRequest(StrictModel):
    match_id: str
    counterparty_id: str
    action: TreatyAction
    treaty_type: TreatyType


class TreatyRecord(StrictModel):
    treaty_id: int = Field(ge=0)
    player_a_id: str
    player_b_id: str
    treaty_type: TreatyType
    status: TreatyStatus
    proposed_by: str
    proposed_tick: TickDuration
    signed_tick: TickDuration | None = None
    withdrawn_by: str | None = None
    withdrawn_tick: TickDuration | None = None


class TreatyListResponse(StrictModel):
    match_id: str
    treaties: list[TreatyRecord] = Field(default_factory=list)


class TreatyActionAcceptanceResponse(StrictModel):
    status: Literal["accepted"]
    match_id: str
    treaty: TreatyRecord


class AllianceActionRequest(StrictModel):
    match_id: str
    action: AllianceAction
    alliance_id: str | None = None
    name: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_action_fields(self) -> Self:
        if self.action == "create":
            if self.alliance_id is not None:
                raise ValueError("alliance create does not accept alliance_id")
            if self.name is None:
                raise ValueError("alliance create requires name")
            return self

        if self.action == "join":
            if self.alliance_id is None:
                raise ValueError("alliance join requires alliance_id")
            if self.name is not None:
                raise ValueError("alliance join does not accept name")
            return self

        if self.alliance_id is not None:
            raise ValueError("alliance leave does not accept alliance_id")
        if self.name is not None:
            raise ValueError("alliance leave does not accept name")
        return self


class AllianceMemberRecord(StrictModel):
    player_id: str
    joined_tick: TickDuration


class AllianceRecord(StrictModel):
    alliance_id: str
    name: str
    leader_id: str
    formed_tick: TickDuration
    members: list[AllianceMemberRecord] = Field(default_factory=list)


class AllianceListResponse(StrictModel):
    match_id: str
    alliances: list[AllianceRecord] = Field(default_factory=list)


class AllianceActionAcceptanceResponse(StrictModel):
    status: Literal["accepted"]
    match_id: str
    player_id: str
    alliance: AllianceRecord | None = None


class AgentCommandMessage(StrictModel):
    channel: CommandMessageChannel
    recipient_id: str | None = None
    group_chat_id: str | None = None
    content: str = Field(min_length=1)


class AgentCommandTreaty(StrictModel):
    counterparty_id: str
    action: TreatyAction
    treaty_type: TreatyType


class AgentCommandAllianceAction(StrictModel):
    action: AllianceAction
    alliance_id: str | None = None
    name: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_action_fields(self) -> Self:
        if self.action == "create":
            if self.alliance_id is not None:
                raise ValueError("alliance create does not accept alliance_id")
            if self.name is None:
                raise ValueError("alliance create requires name")
            return self

        if self.action == "join":
            if self.alliance_id is None:
                raise ValueError("alliance join requires alliance_id")
            if self.name is not None:
                raise ValueError("alliance join does not accept name")
            return self

        if self.alliance_id is not None:
            raise ValueError("alliance leave does not accept alliance_id")
        if self.name is not None:
            raise ValueError("alliance leave does not accept name")
        return self


class AgentCommandEnvelopeResponse(StrictModel):
    status: Literal["accepted"]
    match_id: str
    player_id: str
    tick: TickDuration
    orders: OrderAcceptanceResponse | None = None
    messages: list[MessageAcceptanceResponse | GroupChatMessageAcceptanceResponse] = Field(
        default_factory=list
    )
    treaties: list[TreatyActionAcceptanceResponse] = Field(default_factory=list)
    alliance: AllianceActionAcceptanceResponse | None = None


class AgentBriefingMessageBuckets(StrictModel):
    direct: list[MatchMessageRecord] = Field(default_factory=list)
    group: list[GroupChatMessageRecord] = Field(default_factory=list)
    world: list[MatchMessageRecord] = Field(default_factory=list)


class AgentBriefingGuidanceRecord(StrictModel):
    guidance_id: str
    match_id: str
    player_id: str
    tick: TickDuration
    content: str
    created_at: datetime


class AgentBriefingResponse(StrictModel):
    match_id: str
    player_id: str
    state: AgentStateProjection
    alliances: list[AllianceRecord] = Field(default_factory=list)
    treaties: list[TreatyRecord] = Field(default_factory=list)
    group_chats: list[GroupChatRecord] = Field(default_factory=list)
    messages: AgentBriefingMessageBuckets
    guidance: list[AgentBriefingGuidanceRecord] = Field(default_factory=list)


class SyncRequestSession(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        json: Any = None,
        params: Mapping[str, str | int] | None = None,
    ) -> httpx.Response: ...


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
        *,
        session: SyncRequestSession | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._session = session
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

    def create_match_lobby(
        self,
        *,
        map: Literal["britain"],
        tick_interval_seconds: int,
        max_players: int,
        victory_city_threshold: int,
        starting_cities_per_player: int,
    ) -> MatchLobbyCreateResponse:
        return self._request_json(
            "POST",
            "/api/v1/matches",
            json_body=MatchLobbyCreateRequest(
                map=map,
                tick_interval_seconds=tick_interval_seconds,
                max_players=max_players,
                victory_city_threshold=victory_city_threshold,
                starting_cities_per_player=starting_cities_per_player,
            ),
            response_model=MatchLobbyCreateResponse,
        )

    def join_match(self, match_id: str) -> MatchJoinResponse:
        return self._request_json(
            "POST",
            f"/api/v1/matches/{match_id}/join",
            json_body=MatchJoinRequest(match_id=match_id),
            response_model=MatchJoinResponse,
        )

    def start_match_lobby(self, match_id: str) -> MatchLobbyStartResponse:
        return self._request_json(
            "POST",
            f"/api/v1/matches/{match_id}/start",
            response_model=MatchLobbyStartResponse,
        )

    def get_match_state(self, match_id: str) -> AgentStateProjection:
        return self._request_json(
            "GET",
            f"/api/v1/matches/{match_id}/state",
            response_model=AgentStateProjection,
        )

    def get_agent_briefing(
        self,
        match_id: str,
        *,
        since_tick: int | None = None,
    ) -> AgentBriefingResponse:
        params = None if since_tick is None else {"since_tick": since_tick}
        return self._request_json(
            "GET",
            f"/api/v1/matches/{match_id}/agent-briefing",
            params=params,
            response_model=AgentBriefingResponse,
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

    def submit_command(
        self,
        match_id: str,
        *,
        tick: int,
        orders: OrderBatch | Mapping[str, Any] | None = None,
        messages: list[AgentCommandMessage | Mapping[str, Any]] | None = None,
        treaties: list[AgentCommandTreaty | Mapping[str, Any]] | None = None,
        alliance: AgentCommandAllianceAction | Mapping[str, Any] | None = None,
    ) -> AgentCommandEnvelopeResponse:
        return self._request_json(
            "POST",
            f"/api/v1/matches/{match_id}/command",
            json_body={
                "match_id": match_id,
                "tick": tick,
                "orders": self._model_dump(OrderBatch.model_validate(orders or {})),
                "messages": [
                    self._model_dump(AgentCommandMessage.model_validate(message))
                    for message in (messages or [])
                ],
                "treaties": [
                    self._model_dump(AgentCommandTreaty.model_validate(treaty))
                    for treaty in (treaties or [])
                ],
                "alliance": (
                    None
                    if alliance is None
                    else self._model_dump(AgentCommandAllianceAction.model_validate(alliance))
                ),
            },
            response_model=AgentCommandEnvelopeResponse,
        )

    def submit_command_envelope(
        self,
        match_id: str,
        *,
        tick: int,
        orders: OrderBatch | Mapping[str, Any] | None = None,
        messages: list[AgentCommandMessage | Mapping[str, Any]] | None = None,
        treaties: list[AgentCommandTreaty | Mapping[str, Any]] | None = None,
        alliance: AgentCommandAllianceAction | Mapping[str, Any] | None = None,
    ) -> AgentCommandEnvelopeResponse:
        return self.submit_command(
            match_id,
            tick=tick,
            orders=orders,
            messages=messages,
            treaties=treaties,
            alliance=alliance,
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

    def get_group_chats(self, match_id: str) -> GroupChatListResponse:
        return self._request_json(
            "GET",
            f"/api/v1/matches/{match_id}/group-chats",
            response_model=GroupChatListResponse,
        )

    def create_group_chat(
        self,
        match_id: str,
        *,
        tick: int,
        name: str,
        member_ids: list[str],
    ) -> GroupChatCreateAcceptanceResponse:
        return self._request_json(
            "POST",
            f"/api/v1/matches/{match_id}/group-chats",
            json_body=GroupChatCreateRequest(
                match_id=match_id,
                tick=tick,
                name=name,
                member_ids=member_ids,
            ),
            response_model=GroupChatCreateAcceptanceResponse,
        )

    def get_group_chat_messages(
        self,
        match_id: str,
        *,
        group_chat_id: str,
    ) -> GroupChatMessageListResponse:
        return self._request_json(
            "GET",
            f"/api/v1/matches/{match_id}/group-chats/{group_chat_id}/messages",
            response_model=GroupChatMessageListResponse,
        )

    def send_group_chat_message(
        self,
        match_id: str,
        *,
        group_chat_id: str,
        tick: int,
        content: str,
    ) -> GroupChatMessageAcceptanceResponse:
        return self._request_json(
            "POST",
            f"/api/v1/matches/{match_id}/group-chats/{group_chat_id}/messages",
            json_body=GroupChatMessageCreateRequest(
                match_id=match_id,
                tick=tick,
                content=content,
            ),
            response_model=GroupChatMessageAcceptanceResponse,
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
        params: Mapping[str, str | int] | None = None,
    ) -> ResponseModelT:
        try:
            response = self._send_request(
                method,
                path,
                json_body=None if json_body is None else self._model_dump(json_body),
                params=params,
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
        params: Mapping[str, str | int] | None,
    ) -> httpx.Response:
        request_url = f"{self._base_url}{path}"
        request_headers = {"X-API-Key": self._api_key}
        request_kwargs: dict[str, Any] = {
            "headers": request_headers,
            "json": json_body,
        }
        if params is not None:
            request_kwargs["params"] = params

        if self._session is not None:
            return self._session.request(method, request_url, **request_kwargs)

        with httpx.Client(timeout=self._timeout) as session:
            return session.request(method, request_url, **request_kwargs)

    @staticmethod
    def _model_dump(value: BaseModel | Mapping[str, Any]) -> dict[str, Any]:
        if isinstance(value, BaseModel):
            return dict(value.model_dump(mode="json"))
        return dict(value)


def _rebuild_strict_model_tree(root: type[StrictModel]) -> None:
    for model in root.__subclasses__():
        model.model_rebuild(_types_namespace=globals())
        if issubclass(model, StrictModel):
            _rebuild_strict_model_tree(model)


_rebuild_strict_model_tree(StrictModel)
