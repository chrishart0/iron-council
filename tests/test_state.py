from typing import Any

import pytest
from pydantic import ValidationError
from server.models.domain import NonNegativeCount, StrictModel, UpgradeTrack
from server.models.state import MatchState


def test_match_state_round_trips_representative_payload(
    representative_match_state_payload: dict[str, Any],
) -> None:
    model = MatchState.model_validate(representative_match_state_payload)

    dumped = model.model_dump(mode="json")

    assert dumped == representative_match_state_payload
    assert (
        dumped["cities"]["london"]["building_queue"][0]["type"] == UpgradeTrack.FORTIFICATION.value
    )
    assert MatchState.model_validate(dumped).model_dump(mode="json") == dumped


def test_match_state_rejects_negative_garrison(
    representative_match_state_payload: dict[str, Any],
) -> None:
    representative_match_state_payload["cities"]["london"]["garrison"] = -1

    with pytest.raises(ValidationError):
        MatchState.model_validate(representative_match_state_payload)


def test_non_negative_count_rejects_negative_input() -> None:
    class CountContainer(StrictModel):
        count: NonNegativeCount

    with pytest.raises(ValidationError):
        CountContainer.model_validate({"count": -1})
