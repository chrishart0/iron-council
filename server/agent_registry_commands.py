from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Protocol

from server import agent_registry_diplomacy, agent_registry_messaging
from server.agent_registry_types import MatchRecord
from server.data.maps import load_uk_1900_map
from server.models.api import (
    AgentCommandEnvelopeRequest,
    AgentCommandEnvelopeResponse,
    AllianceActionAcceptanceResponse,
    AllianceActionRequest,
    GroupChatMessageAcceptanceResponse,
    GroupChatMessageCreateRequest,
    MatchMessageCreateRequest,
    MessageAcceptanceResponse,
    OrderAcceptanceResponse,
    TreatyActionAcceptanceResponse,
    TreatyActionRequest,
)
from server.models.orders import OrderBatch, OrderEnvelope
from server.models.state import MatchState
from server.order_validation import validate_order_envelope
from server.resolver import TickPhaseEvent, resolve_tick


@dataclass(frozen=True, slots=True)
class AdvancedTickResult:
    resolved_tick: int
    next_state: MatchState
    accepted_orders: OrderBatch
    events: list[TickPhaseEvent]


class WorldMessageRecorder(Protocol):
    def __call__(self, *, match_id: str, tick: int, content: str) -> None: ...


def _append_scratch_world_message(
    *,
    record: MatchRecord,
    tick: int,
    content: str,
) -> None:
    agent_registry_messaging.append_message(
        record=record,
        channel="world",
        sender_id="system",
        recipient_id=None,
        tick=tick,
        content=content,
    )


def apply_command_envelope(
    *,
    record: MatchRecord,
    match_id: str,
    command: AgentCommandEnvelopeRequest,
    player_id: str,
    record_world_message: WorldMessageRecorder,
) -> AgentCommandEnvelopeResponse:
    scratch_record = deepcopy(record)
    apply_command_envelope_mutations(
        record=scratch_record,
        match_id=match_id,
        command=command,
        player_id=player_id,
        record_world_message=lambda **kwargs: _append_scratch_world_message(
            record=scratch_record,
            tick=kwargs["tick"],
            content=kwargs["content"],
        ),
    )
    return apply_command_envelope_mutations(
        record=record,
        match_id=match_id,
        command=command,
        player_id=player_id,
        record_world_message=record_world_message,
    )


def apply_command_envelope_mutations(
    *,
    record: MatchRecord,
    match_id: str,
    command: AgentCommandEnvelopeRequest,
    player_id: str,
    record_world_message: WorldMessageRecorder,
) -> AgentCommandEnvelopeResponse:
    order_response: OrderAcceptanceResponse | None = None
    message_responses: list[MessageAcceptanceResponse | GroupChatMessageAcceptanceResponse] = []
    treaty_responses: list[TreatyActionAcceptanceResponse] = []
    alliance_response: AllianceActionAcceptanceResponse | None = None

    if command_has_orders(command):
        envelope = OrderEnvelope(
            match_id=match_id,
            player_id=player_id,
            tick=command.tick,
            orders=command.orders,
        )
        record.order_submissions.append(envelope.model_copy(deep=True))
        order_response = OrderAcceptanceResponse(
            status="accepted",
            match_id=match_id,
            player_id=player_id,
            tick=command.tick,
            submission_index=len(record.order_submissions) - 1,
        )

    for message in command.messages:
        agent_registry_messaging.validate_command_message(
            record=record,
            match_id=match_id,
            message=message,
            player_id=player_id,
        )
        if message.channel == "group":
            accepted_group_message = agent_registry_messaging.record_group_chat_message(
                record=record,
                group_chat_id=message.group_chat_id or "",
                message=GroupChatMessageCreateRequest(
                    match_id=match_id,
                    tick=command.tick,
                    content=message.content,
                ),
                sender_id=player_id,
            )
            message_responses.append(
                GroupChatMessageAcceptanceResponse(
                    status="accepted",
                    match_id=match_id,
                    group_chat_id=accepted_group_message.group_chat_id,
                    message=accepted_group_message,
                )
            )
            continue

        accepted_message = agent_registry_messaging.record_message(
            record=record,
            message=MatchMessageCreateRequest(
                match_id=match_id,
                tick=command.tick,
                channel=message.channel,
                recipient_id=message.recipient_id,
                content=message.content,
            ),
            sender_id=player_id,
        )
        message_responses.append(
            MessageAcceptanceResponse(
                status="accepted",
                match_id=match_id,
                message_id=accepted_message.message_id,
                channel=accepted_message.channel,
                sender_id=accepted_message.sender_id,
                recipient_id=accepted_message.recipient_id,
                tick=accepted_message.tick,
                content=accepted_message.content,
            )
        )

    for treaty in command.treaties:
        agent_registry_diplomacy.validate_command_treaty(
            record=record,
            match_id=match_id,
            treaty=treaty,
            player_id=player_id,
        )
        accepted_treaty = agent_registry_diplomacy.apply_treaty_action(
            record=record,
            match_id=match_id,
            action=TreatyActionRequest(
                match_id=match_id,
                counterparty_id=treaty.counterparty_id,
                action=treaty.action,
                treaty_type=treaty.treaty_type,
            ),
            player_id=player_id,
            record_world_message=record_world_message,
        )
        treaty_responses.append(
            TreatyActionAcceptanceResponse(
                status="accepted",
                match_id=match_id,
                treaty=accepted_treaty,
            )
        )

    if command.alliance is not None:
        accepted_alliance = agent_registry_diplomacy.apply_alliance_action(
            record=record,
            match_id=match_id,
            action=AllianceActionRequest(
                match_id=match_id,
                action=command.alliance.action,
                alliance_id=command.alliance.alliance_id,
                name=command.alliance.name,
            ),
            player_id=player_id,
        )
        alliance_response = AllianceActionAcceptanceResponse(
            status="accepted",
            match_id=match_id,
            player_id=player_id,
            alliance=accepted_alliance,
        )

    return AgentCommandEnvelopeResponse(
        status="accepted",
        match_id=match_id,
        player_id=player_id,
        tick=command.tick,
        orders=order_response,
        messages=message_responses,
        treaties=treaty_responses,
        alliance=alliance_response,
    )


def advance_match_tick(*, record: MatchRecord) -> AdvancedTickResult:
    def record_world_message(*, match_id: str, tick: int, content: str) -> None:
        agent_registry_messaging.append_message(
            record=record,
            channel="world",
            sender_id="system",
            recipient_id=None,
            tick=tick,
            content=content,
        )

    current_tick = record.state.tick
    pre_resolution_state = record.state.model_copy(deep=True)
    queued_for_current_tick = [
        submission.model_copy(deep=True)
        for submission in record.order_submissions
        if submission.tick == current_tick
    ]
    record.order_submissions = [
        submission for submission in record.order_submissions if submission.tick != current_tick
    ]

    validated_orders = validate_queued_orders(
        state=record.state,
        submissions=queued_for_current_tick,
    )
    agent_registry_diplomacy.reconcile_hostile_treaty_breaks(
        record=record,
        pre_resolution_state=pre_resolution_state,
        accepted_orders=validated_orders,
        match_id=record.match_id,
        record_world_message=record_world_message,
    )
    resolution = resolve_tick(record.state, validated_orders)
    next_state = resolution.next_state.model_copy(update={"tick": current_tick + 1})
    record.state = next_state
    agent_registry_diplomacy.sync_victory_state(record.state)
    return AdvancedTickResult(
        resolved_tick=record.state.tick,
        next_state=record.state.model_copy(deep=True),
        accepted_orders=validated_orders.model_copy(deep=True),
        events=[event.model_copy(deep=True) for event in resolution.events],
    )


def validate_queued_orders(
    *,
    state: MatchState,
    submissions: list[OrderEnvelope],
) -> OrderBatch:
    aggregated_orders = OrderBatch()
    map_definition = load_uk_1900_map()
    for submission in combine_submissions_by_player(submissions):
        validation = validate_order_envelope(submission, state, map_definition)
        aggregated_orders.movements.extend(
            order.model_copy(deep=True) for order in validation.accepted.movements
        )
        aggregated_orders.recruitment.extend(
            order.model_copy(deep=True) for order in validation.accepted.recruitment
        )
        aggregated_orders.upgrades.extend(
            order.model_copy(deep=True) for order in validation.accepted.upgrades
        )
        aggregated_orders.transfers.extend(
            order.model_copy(deep=True) for order in validation.accepted.transfers
        )
    return aggregated_orders


def combine_submissions_by_player(submissions: list[OrderEnvelope]) -> list[OrderEnvelope]:
    combined_by_player: dict[str, OrderEnvelope] = {}
    ordered_player_ids: list[str] = []
    for submission in submissions:
        combined_submission = combined_by_player.get(submission.player_id)
        if combined_submission is None:
            combined_by_player[submission.player_id] = submission.model_copy(deep=True)
            ordered_player_ids.append(submission.player_id)
            continue
        combined_submission.orders.movements.extend(
            order.model_copy(deep=True) for order in submission.orders.movements
        )
        combined_submission.orders.recruitment.extend(
            order.model_copy(deep=True) for order in submission.orders.recruitment
        )
        combined_submission.orders.upgrades.extend(
            order.model_copy(deep=True) for order in submission.orders.upgrades
        )
        combined_submission.orders.transfers.extend(
            order.model_copy(deep=True) for order in submission.orders.transfers
        )
    return [combined_by_player[player_id] for player_id in ordered_player_ids]


def command_has_orders(command: AgentCommandEnvelopeRequest) -> bool:
    return any(
        (
            command.orders.movements,
            command.orders.recruitment,
            command.orders.upgrades,
            command.orders.transfers,
        )
    )
