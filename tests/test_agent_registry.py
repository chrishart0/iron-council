from __future__ import annotations

from server.agent_registry import InMemoryMatchRegistry, MatchRecord
from server.models.api import AllianceActionRequest
from server.models.domain import MatchStatus
from server.models.state import MatchState


def test_join_initializes_victory_countdown_for_new_sole_leader() -> None:
    registry = InMemoryMatchRegistry()
    registry.seed_match(
        MatchRecord(
            match_id="countdown-match",
            status=MatchStatus.ACTIVE,
            tick_interval_seconds=30,
            state=MatchState.model_validate(
                {
                    "tick": 12,
                    "cities": {
                        "alpha": {
                            "owner": "player-1",
                            "population": 5,
                            "resources": {"food": 1, "production": 1, "money": 1},
                            "upgrades": {"economy": 0, "military": 0, "fortification": 0},
                            "garrison": 3,
                            "building_queue": [],
                        },
                        "beta": {
                            "owner": "player-2",
                            "population": 5,
                            "resources": {"food": 1, "production": 1, "money": 1},
                            "upgrades": {"economy": 0, "military": 0, "fortification": 0},
                            "garrison": 3,
                            "building_queue": [],
                        },
                    },
                    "players": {
                        "player-1": {
                            "resources": {"food": 5, "production": 5, "money": 5},
                            "cities_owned": ["alpha"],
                            "alliance_id": None,
                            "is_eliminated": False,
                        },
                        "player-2": {
                            "resources": {"food": 5, "production": 5, "money": 5},
                            "cities_owned": ["beta"],
                            "alliance_id": None,
                            "is_eliminated": False,
                        },
                    },
                    "victory": {
                        "leading_alliance": None,
                        "cities_held": 1,
                        "threshold": 2,
                        "countdown_ticks_remaining": None,
                    },
                }
            ),
        )
    )

    created_alliance = registry.apply_alliance_action(
        match_id="countdown-match",
        action=AllianceActionRequest(
            match_id="countdown-match",
            player_id="player-1",
            action="create",
            name="Northern Pact",
        ),
    )
    joined_alliance = registry.apply_alliance_action(
        match_id="countdown-match",
        action=AllianceActionRequest(
            match_id="countdown-match",
            player_id="player-2",
            action="join",
            alliance_id=created_alliance.alliance_id if created_alliance is not None else None,
            name=None,
        ),
    )

    assert joined_alliance is not None
    match = registry.get_match("countdown-match")
    assert match is not None
    assert match.state.victory.model_dump(mode="json") == {
        "leading_alliance": joined_alliance.alliance_id,
        "cities_held": 2,
        "threshold": 2,
        "countdown_ticks_remaining": 2,
    }


def test_sync_victory_state_ignores_unowned_and_unknown_city_holders() -> None:
    registry = InMemoryMatchRegistry()
    state = MatchState.model_validate(
        {
            "tick": 8,
            "cities": {
                "alpha": {
                    "owner": None,
                    "population": 5,
                    "resources": {"food": 1, "production": 1, "money": 1},
                    "upgrades": {"economy": 0, "military": 0, "fortification": 0},
                    "garrison": 3,
                    "building_queue": [],
                },
                "beta": {
                    "owner": "ghost-player",
                    "population": 5,
                    "resources": {"food": 1, "production": 1, "money": 1},
                    "upgrades": {"economy": 0, "military": 0, "fortification": 0},
                    "garrison": 3,
                    "building_queue": [],
                },
            },
            "players": {
                "player-1": {
                    "resources": {"food": 5, "production": 5, "money": 5},
                    "cities_owned": [],
                    "alliance_id": None,
                    "is_eliminated": False,
                }
            },
            "victory": {
                "leading_alliance": "alliance-red",
                "cities_held": 2,
                "threshold": 2,
                "countdown_ticks_remaining": 1,
            },
        }
    )

    registry._sync_victory_state(state)  # noqa: SLF001

    assert state.victory.model_dump(mode="json") == {
        "leading_alliance": None,
        "cities_held": 0,
        "threshold": 2,
        "countdown_ticks_remaining": None,
    }


def test_sync_victory_state_reinitializes_missing_countdown_for_same_leader() -> None:
    registry = InMemoryMatchRegistry()
    state = MatchState.model_validate(
        {
            "tick": 8,
            "cities": {
                "alpha": {
                    "owner": "player-1",
                    "population": 5,
                    "resources": {"food": 1, "production": 1, "money": 1},
                    "upgrades": {"economy": 0, "military": 0, "fortification": 0},
                    "garrison": 3,
                    "building_queue": [],
                },
                "beta": {
                    "owner": "player-2",
                    "population": 5,
                    "resources": {"food": 1, "production": 1, "money": 1},
                    "upgrades": {"economy": 0, "military": 0, "fortification": 0},
                    "garrison": 3,
                    "building_queue": [],
                },
            },
            "players": {
                "player-1": {
                    "resources": {"food": 5, "production": 5, "money": 5},
                    "cities_owned": ["alpha"],
                    "alliance_id": "alliance-red",
                    "is_eliminated": False,
                },
                "player-2": {
                    "resources": {"food": 5, "production": 5, "money": 5},
                    "cities_owned": ["beta"],
                    "alliance_id": "alliance-red",
                    "is_eliminated": False,
                },
            },
            "victory": {
                "leading_alliance": "alliance-red",
                "cities_held": 2,
                "threshold": 2,
                "countdown_ticks_remaining": None,
            },
        }
    )

    registry._sync_victory_state(state)  # noqa: SLF001

    assert state.victory.model_dump(mode="json") == {
        "leading_alliance": "alliance-red",
        "cities_held": 2,
        "threshold": 2,
        "countdown_ticks_remaining": 2,
    }
