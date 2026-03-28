import pytest
from pydantic import ValidationError

from server.models.state import MatchState


def test_match_state_round_trip(match_state_payload: dict) -> None:
    state = MatchState.model_validate(match_state_payload)

    dumped = state.model_dump(mode="json")

    assert dumped == match_state_payload
    assert MatchState.model_validate(dumped).model_dump(mode="json") == dumped


def test_army_state_validation_requires_path_when_destination_is_set(
    match_state_payload: dict,
) -> None:
    match_state_payload["armies"][1]["path"] = None

    with pytest.raises(ValidationError):
        MatchState.model_validate(match_state_payload)
