import pytest
from pydantic import ValidationError

from server.models.orders import OrderEnvelope


def test_order_envelope_round_trip(order_envelope_payload: dict) -> None:
    envelope = OrderEnvelope.model_validate(order_envelope_payload)

    dumped = envelope.model_dump(mode="json")

    assert dumped["match_id"] == order_envelope_payload["match_id"]
    assert dumped["player_id"] == order_envelope_payload["player_id"]
    assert dumped["tick"] == order_envelope_payload["tick"]
    assert dumped["orders"]["movements"][0]["type"] == "movement"
    assert dumped["orders"]["recruitment"][0]["type"] == "recruitment"
    assert dumped["orders"]["upgrades"][0]["type"] == "upgrade"
    assert dumped["orders"]["transfers"][0]["type"] == "transfer"
    assert OrderEnvelope.model_validate(dumped).model_dump(mode="json") == dumped


def test_order_validation_rejects_invalid_transfer_amount(
    order_envelope_payload: dict,
) -> None:
    order_envelope_payload["orders"]["transfers"][0]["amount"] = 0

    with pytest.raises(ValidationError):
        OrderEnvelope.model_validate(order_envelope_payload)
