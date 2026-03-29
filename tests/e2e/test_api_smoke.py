from __future__ import annotations

from copy import deepcopy
from http import HTTPStatus
from typing import Any

import httpx
from tests.support import RunningApp


def test_agent_api_smoke_flow_runs_through_real_process_and_seeded_database(
    running_seeded_app: RunningApp,
    representative_order_payload: dict[str, Any],
) -> None:
    payload = deepcopy(representative_order_payload)
    payload["match_id"] = running_seeded_app.primary_match_id
    payload["player_id"] = "player-1"
    payload["tick"] = 142
    payload["orders"] = {
        **payload["orders"],
        "movements": [{"army_id": "army-b", "destination": "birmingham"}],
    }

    with httpx.Client(base_url=running_seeded_app.base_url, timeout=5) as client:
        health_response = client.get("/health")
        list_response = client.get("/api/v1/matches")
        initial_state_response = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/state",
            params={"player_id": "player-1"},
        )
        submit_response = client.post(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/orders",
            json=payload,
        )
        follow_up_state_response = client.get(
            f"/api/v1/matches/{running_seeded_app.primary_match_id}/state",
            params={"player_id": "player-1"},
        )

    assert health_response.status_code == HTTPStatus.OK
    assert list_response.status_code == HTTPStatus.OK
    assert [match["match_id"] for match in list_response.json()["matches"]] == [
        running_seeded_app.primary_match_id,
        running_seeded_app.secondary_match_id,
    ]
    assert initial_state_response.status_code == HTTPStatus.OK
    assert submit_response.status_code == HTTPStatus.ACCEPTED
    assert submit_response.json() == {
        "status": "accepted",
        "match_id": running_seeded_app.primary_match_id,
        "player_id": "player-1",
        "tick": 142,
        "submission_index": 0,
    }
    assert follow_up_state_response.status_code == HTTPStatus.OK
    assert follow_up_state_response.json() == initial_state_response.json()
