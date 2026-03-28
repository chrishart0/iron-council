from typing import Any

import pytest
from pydantic import ValidationError
from server.models.domain import ResourceType, UpgradeTrack
from server.models.orders import OrderEnvelope


def test_order_envelope_round_trips_representative_payload(
    representative_order_payload: dict[str, Any],
) -> None:
    model = OrderEnvelope.model_validate(representative_order_payload)

    dumped = model.model_dump(mode="json")

    assert dumped == representative_order_payload
    assert dumped["orders"]["upgrades"][0]["track"] == UpgradeTrack.FORTIFICATION.value
    assert dumped["orders"]["upgrades"][0]["target_tier"] == 1
    assert dumped["orders"]["transfers"][0]["resource"] == ResourceType.MONEY.value
    assert OrderEnvelope.model_validate(dumped).model_dump(mode="json") == dumped


def test_order_envelope_rejects_invalid_transfer_amount(
    representative_order_payload: dict[str, Any],
) -> None:
    representative_order_payload["orders"]["transfers"][0]["amount"] = -1

    with pytest.raises(ValidationError):
        OrderEnvelope.model_validate(representative_order_payload)
